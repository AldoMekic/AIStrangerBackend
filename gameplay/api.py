from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Game, Character
from .serializers import GameSerializer

# Import the "Agent Programs" implemented previously
from ai_logic.adversarial_search import DemogorgonAgent
from ai_logic.informed_search import ShadowmonsterAgent
from ai_logic.stochastic_search import MindflayerAgent

class GameViewSet(viewsets.ModelViewSet):
    """
    The View Layer that handles the logic of processing requests 
    and returning environment responses [3].
    """
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    @action(detail=True, methods=['post'])
    def play_turn(self, request, pk=None):
        """
        Main endpoint for the 'Execute' phase of the problem-solving agent [6].
        Receives a move from React, validates it, and triggers the AI response.
        """
        game = self.get_object()
        if game.is_over:
            return Response({"error": "Game is already over"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. PERCEPT PHASE: Receive player input (The 'Sensor' data) [7, 8]
        # logic for move validation from game_engine/validators.py should go here

        # 2. UPDATE STATE: Apply the result of the player move [1, 9]
        # result = rules.apply_move(game, request.data)
        
        # 3. AGENT PROGRAM PHASE: Trigger AI if in PVA mode [4, 10]
        if game.game_mode == 'PVA' and not game.is_over:
            # Select the correct agent based on the difficulty level requirement
            agent = self._get_agent(game.difficulty_level)
            
            # The agent receives the current state and returns an action [8, 11]
            # ai_action = agent.get_action(game)
            
            # Apply the AI's action to the database models
            # rules.apply_move(game, ai_action)

        # 4. ACTUATOR PHASE: Send back the JSON state for React to animate [7, 12]
        serializer = self.get_serializer(game)
        return Response(serializer.data)

    def _get_agent(self, level):
        """
        Internal mapping of Level Requirements to implemented AI Agents.
        """
        if level in [11, 13]:
            return DemogorgonAgent()
        elif level == 3:
            return ShadowmonsterAgent()
        elif level == 4:
            return MindflayerAgent()
        return None