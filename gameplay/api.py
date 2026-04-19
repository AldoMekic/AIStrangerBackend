from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Game
from .serializers import GameSerializer
from .state import GameState

from ai_logic.adversarial_search import DemogorgonAgent
from ai_logic.informed_search import ShadowmonsterAgent
from ai_logic.stochastic_search import MindflayerAgent


class GameViewSet(viewsets.ModelViewSet):
    """
    View layer responsible for:
    - loading persisted Django game state
    - validating incoming player actions
    - applying rules
    - triggering AI response
    - persisting the updated state
    """
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    @action(detail=True, methods=["post"])
    def play_turn(self, request, pk=None):
        game = self.get_object()

        if game.is_over:
            return Response(
                {"error": "Game is already over"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Build in-memory domain state from Django models
        state = GameState.from_game(game)

        # 2. Ensure the player is the one acting
        if state.current_turn != "ELEVEN":
            return Response(
                {"error": f"It is currently {state.current_turn}'s turn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Parse and validate incoming action
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

        # 4. Apply player move
        state = state.result(player_action)
        self._finalize_terminal_state(state)

        # 5. If player move ends the game, persist and return immediately
        if state.is_terminal():
            state.apply_to_game(game)
            serializer = self.get_serializer(game)
            return Response(serializer.data)

        # 6. Trigger AI in PVA mode
        if state.game_mode == "PVA":
            agent = self._get_agent(state.difficulty_level)

            if agent is None:
                return Response(
                    {"error": "No AI agent configured for this difficulty."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            ai_action = self._get_ai_action(agent, state)

            if ai_action is None:
                # No available move for AI; treat as end/frozen state for now
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

        # 7. Persist final state back to Django
        state.apply_to_game(game)

        # 8. Return updated snapshot for React
        serializer = self.get_serializer(game)
        return Response(serializer.data)

    def _get_agent(self, level):
        """
        Correct mapping of difficulty level to AI agent.
        """
        if level in [1, 2]:
            return DemogorgonAgent()
        if level == 3:
            return ShadowmonsterAgent()
        if level == 4:
            return MindflayerAgent()
        return None

    def _get_ai_action(self, agent, state):
        """
        Dispatch agent decision according to the selected difficulty.
        """
        if state.difficulty_level in [1, 2]:
            return agent.get_action(state, level=state.difficulty_level)
        return agent.get_action(state)

    def _parse_action(self, payload):
        """
        Minimal request parsing for current gameplay actions.

        Supported formats:
        - MOVE: {"type": "MOVE", "direction": "UP"}
        - TELEPORT: {"type": "TELEPORT", "destination": [x, y]}
        """
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
        """
        Compare normalized actions safely.
        """
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
        """
        Set is_over and winner consistently after each move.
        """
        if state.player_at_goal():
            state.is_over = True
            state.winner = "ELEVEN"
            return

        for enemy in ("DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"):
            if enemy in state.characters and state.get_position(enemy) == state.get_position("ELEVEN"):
                state.is_over = True
                state.winner = enemy
                return

        state.is_over = False
        state.winner = None