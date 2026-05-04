import random

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Game, Character, Obstacle
from .serializers import GameSerializer, ActionSerializer
from .state import GameState

from ai_logic.adversarial_search import DemogorgonAgent
from ai_logic.informed_search import ShadowmonsterAgent
from ai_logic.stochastic_search import MindflayerAgent


class GameViewSet(viewsets.ModelViewSet):
    """
    View layer responsible for:
    - creating initialized game worlds
    - loading persisted Django game state
    - validating incoming player actions
    - applying rules
    - triggering AI response
    - persisting the updated state
    """
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def create(self, request, *args, **kwargs):
        """
        Custom game creation that initializes a playable world.
        """
        grid_size = request.data.get("grid_size", 5)
        game_mode = request.data.get("game_mode", "PVA")
        difficulty_level = request.data.get("difficulty_level", 1)

        try:
            grid_size = int(grid_size)
            difficulty_level = int(difficulty_level)
        except (TypeError, ValueError):
            return Response(
                {"error": "grid_size and difficulty_level must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if grid_size not in [5, 6, 7, 8]:
            return Response(
                {"error": "grid_size must be between 5 and 8."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if game_mode not in ["PVP", "PVA", "P2VA"]:
            return Response(
                {"error": "game_mode must be either 'PVP', 'PVA' or 'P2VA'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if difficulty_level not in [1, 2, 3, 4]:
            return Response(
                {"error": "difficulty_level must be between 1 and 4."},
                status=status.HTTP_400_BAD_REQUEST,
            )


        goal_position = (grid_size - 1, grid_size - 1)
        reserved_positions = {goal_position}

        # Create game root
        game = Game.objects.create(
            grid_size=grid_size,
            game_mode=game_mode,
            difficulty_level=difficulty_level,
            current_turn="ELEVEN",
            is_over=False,
            winner=None,
            goal_x=goal_position[0],
            goal_y=goal_position[1],
        )

        # Place Eleven
        eleven_pos = self._choose_player_start(grid_size, reserved_positions)
        reserved_positions.add(eleven_pos)

        Character.objects.create(
            game=game,
            name="ELEVEN",
            x_pos=eleven_pos[0],
            y_pos=eleven_pos[1],
            has_powers=self._player_starts_with_powers("ELEVEN"),
            is_ai=False,
            stuck=False,
        )

        if game_mode in ["PVP", "P2VA"]:
            max_pos = self._choose_second_player_start(grid_size, reserved_positions, eleven_pos)
            reserved_positions.add(max_pos)

            Character.objects.create(
                game=game,
                name="MAX",
                x_pos=max_pos[0],
                y_pos=max_pos[1],
                has_powers=self._player_starts_with_powers("MAX"),
                is_ai=False,
                stuck=False,
            )

        # PVA: create exactly one AI enemy based on selected level
        if game_mode in ["PVA", "P2VA"]:
            enemy_name = self._get_enemy_name_for_level(difficulty_level)

            anchor_pos = eleven_pos
            if game_mode == "P2VA":
                anchor_pos = max(
                    [eleven_pos, max_pos],
                    key=lambda p: self._manhattan_distance(p, goal_position)
                )

            enemy_pos = self._choose_enemy_start(grid_size, reserved_positions, anchor_pos)
            reserved_positions.add(enemy_pos)

            Character.objects.create(
                game=game,
                name=enemy_name,
                x_pos=enemy_pos[0],
                y_pos=enemy_pos[1],
                has_powers=self._ai_starts_with_powers(enemy_name),
                is_ai=True,
                stuck=False,
            )

        # Generate safe obstacles
        self._create_obstacles(game, reserved_positions)

        serializer = self.get_serializer(game)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def play_turn(self, request, pk=None):
        game = self.get_object()

        if game.is_over:
            return Response(
                {"error": "Game is already over"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = GameState.from_game(game)

        if state.game_mode == "PVA":
            allowed_human_turns = {"ELEVEN"}
        elif state.game_mode in ["PVP", "P2VA"]:
            allowed_human_turns = {"ELEVEN", "MAX"}
        else:
            allowed_human_turns = {"ELEVEN"}

        if state.current_turn not in allowed_human_turns:
            return Response(
                {"error": f"It is currently {state.current_turn}'s turn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action_serializer = ActionSerializer(data=request.data)

        if not action_serializer.is_valid():
            return Response(
                action_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        player_actor = state.current_turn
        before_player_state = state.clone()

        player_action = action_serializer.validated_data

        legal_actions = state.get_legal_moves()
        if not self._action_in_list(player_action, legal_actions):
            return Response(
                {
                    "error": "Illegal move.",
                    "legal_actions": legal_actions,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = state.result(player_action)
        self._finalize_terminal_state(state)

        last_event = self._build_event(
            actor=player_actor,
            action=player_action,
            state_before=before_player_state,
            state_after=state,
        )

        last_event = self._build_event(
            actor=ai_actor,
            action=ai_action,
            state_before=before_ai_state,
            state_after=state,
        )

        if state.is_terminal():
            state.apply_to_game(game)
            serializer = self.get_serializer(game)
            return Response(serializer.data)

        if state.game_mode in ["PVA", "P2VA"]:
            ai_name = self._get_enemy_name_for_level(state.difficulty_level)

            if state.current_turn == ai_name:
                agent = self._get_agent(state.difficulty_level)

                if agent is None:
                    return Response(
                        {"error": "No AI agent configured for this difficulty."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                ai_actor = state.current_turn
                before_ai_state = state.clone()
                ai_action = self._get_ai_action(agent, state)

                if ai_action is None:
                    state.advance_turn()
                else:
                    ai_legal_actions = state.get_legal_moves()

                    if not self._action_in_list(ai_action, ai_legal_actions):
                        return Response(
                            {
                                "error": "AI produced an illegal move.",
                                "ai_action": ai_action,
                                "legal_actions": ai_legal_actions,
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                    state = state.result(ai_action)
                    self._finalize_terminal_state(state)

        state.apply_to_game(game)
        serializer = self.get_serializer(game, context={"last_event": last_event})
        return Response(serializer.data)

    def _get_agent(self, level):
        if level in [1, 2]:
            return DemogorgonAgent()
        if level == 3:
            return ShadowmonsterAgent()
        if level == 4:
            return MindflayerAgent()
        return None

    def _get_ai_action(self, agent, state):
        if state.difficulty_level in [1, 2]:
            return agent.get_action(state, level=state.difficulty_level)
        return agent.get_action(state)

    def _action_in_list(self, action, legal_actions):
        normalized_target = self._normalize_action(action)
        normalized_legal = [self._normalize_action(a) for a in legal_actions]
        return normalized_target in normalized_legal

    def _normalize_action(self, action):
        if action["type"] == "MOVE":
            return {
                "type": "MOVE",
                "direction": action["direction"],
            }

        if action["type"] == "TELEPORT":
            destination = action["destination"]
            return {
                "type": "TELEPORT",
                "destination": tuple(destination),
            }

        return action

    def _finalize_terminal_state(self, state):
        if state.goal_position is not None:
            for player_name in ("ELEVEN", "MAX"):
                if player_name in state.characters and state.get_position(player_name) == state.goal_position:
                    state.is_over = True
                    state.winner = player_name
                    return

        if state.game_mode in ["PVA", "P2VA"]:
            for enemy in ("DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"):
                if enemy not in state.characters:
                    continue

                for player_name in ("ELEVEN", "MAX"):
                    if player_name in state.characters and state.get_position(enemy) == state.get_position(player_name):
                        state.is_over = True
                        state.winner = enemy
                        return

        state.is_over = False
        state.winner = None

    def _get_enemy_name_for_level(self, difficulty_level):
        if difficulty_level in [1, 2]:
            return "DEMOGORGON"
        if difficulty_level == 3:
            return "SHADOWMONSTER"
        return "MINDFLAYER"

    def _choose_player_start(self, grid_size, reserved_positions):
        """
        Start Eleven near top-left, but never on reserved cells.
        """
        preferred_positions = [
            (0, 0),
            (1, 0),
            (0, 1),
            (1, 1),
        ]

        for pos in preferred_positions:
            if self._is_within_bounds(pos, grid_size) and pos not in reserved_positions:
                return pos

        return self._random_free_cell(grid_size, reserved_positions)

    def _choose_enemy_start(self, grid_size, reserved_positions, player_pos):
        """
        Start enemy far from Eleven and never on reserved cells.
        """
        candidates = []
        for x in range(grid_size):
            for y in range(grid_size):
                pos = (x, y)
                if pos in reserved_positions:
                    continue

                dist = self._manhattan_distance(pos, player_pos)
                candidates.append((dist, pos))

        candidates.sort(reverse=True, key=lambda item: item[0])

        # Choose among the farthest few to keep starts varied
        top = [pos for _, pos in candidates[:5]] if candidates else []
        if top:
            return random.choice(top)

        return self._random_free_cell(grid_size, reserved_positions)
    

    def _board_is_playable(self, grid_size, goal_position, player_positions, ai_positions, obstacles):
        """
        Checks whether the board remains playable after adding obstacles.

        VEIN is treated as blocking.
        TRAP is treated as passable.
        """
        blocked = {
            pos
            for pos, obstacle_type in obstacles
            if obstacle_type == "VEIN"
        }

        for player_pos in player_positions:
            if not self._path_exists(grid_size, player_pos, goal_position, blocked):
                return False

        if ai_positions and player_positions:
            for ai_pos in ai_positions:
                if not any(
                    self._path_exists(grid_size, ai_pos, player_pos, blocked)
                    for player_pos in player_positions
                ):
                    return False

        return True


    def _path_exists(self, grid_size, start, goal, blocked):
        """
        Breadth-first search to confirm that a path exists.
        """
        if start in blocked or goal in blocked:
            return False

        queue = [start]
        visited = {start}

        while queue:
            current = queue.pop(0)

            if current == goal:
                return True

            for neighbor in self._get_grid_neighbors(current, grid_size):
                if neighbor in visited:
                    continue

                if neighbor in blocked:
                    continue

                visited.add(neighbor)
                queue.append(neighbor)

        return False


    def _get_grid_neighbors(self, pos, grid_size):
        x, y = pos
        candidates = [
            (x, y - 1),
            (x, y + 1),
            (x - 1, y),
            (x + 1, y),
        ]

        return [
            p for p in candidates
            if self._is_within_bounds(p, grid_size)
        ]



    def _create_obstacles(self, game, reserved_positions):
        """
        Create obstacles while preserving basic playability.

        Guarantees:
        - goal cell remains free
        - spawn cells remain free
        - Eleven can reach the goal
        - Max can reach the goal, if present
        - AI can reach at least one player, if present
        """
        grid_size = game.grid_size
        total_cells = grid_size * grid_size
        obstacle_count = max(2, total_cells // 6)

        characters = list(game.characters.all())

        player_positions = [
            (ch.x_pos, ch.y_pos)
            for ch in characters
            if ch.name in ["ELEVEN", "MAX"]
        ]

        ai_positions = [
            (ch.x_pos, ch.y_pos)
            for ch in characters
            if ch.is_ai
        ]

        goal_position = (game.goal_x, game.goal_y)

        candidate_positions = [
            (x, y)
            for x in range(grid_size)
            for y in range(grid_size)
            if (x, y) not in reserved_positions
        ]

        random.shuffle(candidate_positions)

        placed_obstacles = []

        for pos in candidate_positions:
            if len(placed_obstacles) >= obstacle_count:
                break

            obstacle_type = "VEIN" if len(placed_obstacles) % 2 == 0 else "TRAP"

            test_obstacles = placed_obstacles + [(pos, obstacle_type)]

            if self._board_is_playable(
                grid_size=grid_size,
                goal_position=goal_position,
                player_positions=player_positions,
                ai_positions=ai_positions,
                obstacles=test_obstacles,
            ):
                placed_obstacles.append((pos, obstacle_type))

        for pos, obstacle_type in placed_obstacles:
            Obstacle.objects.create(
                game=game,
                obstacle_type=obstacle_type,
                x_pos=pos[0],
                y_pos=pos[1],
            )

    def _random_free_cell(self, grid_size, reserved_positions):
        candidates = [
            (x, y)
            for x in range(grid_size)
            for y in range(grid_size)
            if (x, y) not in reserved_positions
        ]
        if not candidates:
            raise ValueError("No free cell available for placement.")
        return random.choice(candidates)

    def _manhattan_distance(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _is_within_bounds(self, pos, grid_size):
        x, y = pos
        return 0 <= x < grid_size and 0 <= y < grid_size
    
    def _choose_second_player_start(self, grid_size, reserved_positions, first_player_pos):
        """
        Start the second player away from Eleven, but not on reserved cells.
        """
        candidates = []
        for x in range(grid_size):
            for y in range(grid_size):
                pos = (x, y)
                if pos in reserved_positions:
                    continue

                dist = self._manhattan_distance(pos, first_player_pos)
                candidates.append((dist, pos))

        candidates.sort(reverse=True, key=lambda item: item[0])

        top = [pos for _, pos in candidates[:5]] if candidates else []
        if top:
            return random.choice(top)

        return self._random_free_cell(grid_size, reserved_positions)
    
    def _build_event(self, actor, action, state_before, state_after):
        event = {
            "actor": actor,
            "action_type": action["type"],
            "teleport_used": action["type"] == "TELEPORT",
            "trap_triggered": False,
            "end_reason": None,
        }

        before_pos = state_before.get_position(actor) if actor in state_before.characters else None
        after_pos = state_after.get_position(actor) if actor in state_after.characters else None

        event["from"] = list(before_pos) if before_pos else None
        event["to"] = list(after_pos) if after_pos else None

        if after_pos is not None and state_after.get_obstacle_at(after_pos) == "TRAP":
            event["trap_triggered"] = True

        if state_after.is_over:
            if state_after.winner in {"ELEVEN", "MAX"}:
                event["end_reason"] = "PLAYER_REACHED_GOAL"
            elif state_after.winner in {"DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"}:
                event["end_reason"] = "PLAYER_CAUGHT"
            else:
                event["end_reason"] = "GAME_OVER"

        return event
    
    def _player_starts_with_powers(self, character_name):
        """
        Hidden powers rule:
        - ELEVEN starts with hidden powers.
        - MAX starts with hidden powers.
        - AI enemies do not start with hidden powers.
        - Teleport is single-use because GameRules.result() sets has_powers=False after TELEPORT.
        """
        return character_name in {"ELEVEN", "MAX"}


    def _ai_starts_with_powers(self, character_name):
        """
        AI enemies currently do not use hidden powers.
        """
        return False