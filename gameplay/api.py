import random

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Game, Character, Obstacle
from .serializers import GameSerializer
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

        if game_mode not in ["PVP", "PVA"]:
            return Response(
                {"error": "game_mode must be either 'PVP' or 'PVA'."},
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
            has_powers=True,
            is_ai=False,
            stuck=False,
        )

        if game_mode == "PVP":
            max_pos = self._choose_second_player_start(grid_size, reserved_positions, eleven_pos)
            reserved_positions.add(max_pos)

            Character.objects.create(
                game=game,
                name="MAX",
                x_pos=max_pos[0],
                y_pos=max_pos[1],
                has_powers=True,
                is_ai=False,
                stuck=False,
            )

        # PVA: create exactly one AI enemy based on selected level
        if game_mode == "PVA":
            enemy_name = self._get_enemy_name_for_level(difficulty_level)
            enemy_pos = self._choose_enemy_start(grid_size, reserved_positions, eleven_pos)
            reserved_positions.add(enemy_pos)

            Character.objects.create(
                game=game,
                name=enemy_name,
                x_pos=enemy_pos[0],
                y_pos=enemy_pos[1],
                has_powers=False,
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

        allowed_human_turns = {"ELEVEN"} if state.game_mode == "PVA" else {"ELEVEN", "MAX"}

        if state.current_turn not in allowed_human_turns:
            return Response(
                {"error": f"It is currently {state.current_turn}'s turn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        player_action = self._parse_action(request.data)
        if player_action is None:
            return Response(
                {"error": "Invalid action payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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

        if state.is_terminal():
            state.apply_to_game(game)
            serializer = self.get_serializer(game)
            return Response(serializer.data)

        if state.game_mode == "PVA":
            agent = self._get_agent(state.difficulty_level)

            if agent is None:
                return Response(
                    {"error": "No AI agent configured for this difficulty."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            ai_action = self._get_ai_action(agent, state)

            if ai_action is None:
                state.is_over = True
                state.winner = "ELEVEN"
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
        serializer = self.get_serializer(game)
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

    def _parse_action(self, payload):
        action_type = payload.get("type")

        if action_type == "MOVE":
            direction = payload.get("direction")
            if direction in {"UP", "DOWN", "LEFT", "RIGHT"}:
                return {"type": "MOVE", "direction": direction}
            return None

        if action_type == "TELEPORT":
            destination = payload.get("destination")
            if (
                isinstance(destination, (list, tuple))
                and len(destination) == 2
                and all(isinstance(v, int) for v in destination)
            ):
                return {
                    "type": "TELEPORT",
                    "destination": (destination[0], destination[1]),
                }
            return None

        return None

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

        if state.game_mode == "PVA":
            for enemy in ("DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"):
                if enemy in state.characters and state.get_position(enemy) == state.get_position("ELEVEN"):
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

    def _create_obstacles(self, game, reserved_positions):
        """
        Create a moderate number of safe obstacles.
        Keeps spawn cells and goal cell free.
        """
        grid_size = game.grid_size
        total_cells = grid_size * grid_size

        # Conservative obstacle density for playability
        obstacle_count = max(2, total_cells // 6)

        available_positions = [
            (x, y)
            for x in range(grid_size)
            for y in range(grid_size)
            if (x, y) not in reserved_positions
        ]

        random.shuffle(available_positions)
        chosen_positions = available_positions[:obstacle_count]

        for idx, pos in enumerate(chosen_positions):
            obstacle_type = "VEIN" if idx % 2 == 0 else "TRAP"
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