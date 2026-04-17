import math

# Define infinity for minimax initialization [7, 8]
INFINITY = math.inf

class DemogorgonAgent:
    """
    AI Agent representing the Demogorgon.
    Implements Level 1 (Minimax) and Level 2 (Alpha-Beta Pruning).
    """

    def __init__(self, depth_limit=3):
        self.depth_limit = depth_limit

    def get_action(self, game_state, level=1):
        """
        Decision entry point based on the selected game level [Requirement].
        """
        if level == 1:
            return self.minimax_decision(game_state)
        elif level == 2:
            return self.alpha_beta_search(game_state)
        return None

    # --- LEVEL 1: MINIMAX ALGORITHM [1, 2, 9] ---

    def minimax_decision(self, state):
        """
        Returns the action that leads to the state with the highest 
        minimax value [2].
        """
        # We want to maximize the outcome for the Demogorgon
        best_score = -INFINITY
        best_move = None

        for action in state.get_legal_moves():
            # Generate the resulting state for this move [5]
            successor_state = state.result(action)
            # Find the minimum value the opponent (Player) can force [10]
            v = self.min_value(successor_state, 1)
            
            if v > best_score:
                best_score = v
                best_move = action
        
        return best_move

    def max_value(self, state, depth):
        if state.is_terminal() or depth >= self.depth_limit:
            return state.utility("Demogorgon") # [5, 11]
        
        v = -INFINITY
        for action in state.get_legal_moves():
            v = max(v, self.min_value(state.result(action), depth + 1))
        return v

    def min_value(self, state, depth):
        if state.is_terminal() or depth >= self.depth_limit:
            return state.utility("Demogorgon")
        
        v = INFINITY
        for action in state.get_legal_moves():
            v = min(v, self.max_value(state.result(action), depth + 1))
        return v


    # --- LEVEL 2: ALPHA-BETA PRUNING [3, 4, 12] ---

    def alpha_beta_search(self, state):
        """
        Returns an action using alpha-beta pruning to eliminate 
        irrelevant branches [3, 13].
        """
        # alpha: value of best choice found so far for MAX [14]
        # beta: value of best choice found so far for MIN [14]
        best_score, best_move = self.ab_max_value(state, 0, -INFINITY, INFINITY)
        return best_move

    def ab_max_value(self, state, depth, alpha, beta):
        if state.is_terminal() or depth >= self.depth_limit:
            return state.utility("Demogorgon"), None
        
        v = -INFINITY
        best_move = None
        
        for action in state.get_legal_moves():
            current_v, _ = self.ab_min_value(state.result(action), depth + 1, alpha, beta)
            
            if current_v > v:
                v = current_v
                best_move = action
            
            # Pruning condition: if v >= beta, return v [3, 12]
            if v >= beta:
                return v, best_move
            
            alpha = max(alpha, v)
            
        return v, best_move

    def ab_min_value(self, state, depth, alpha, beta):
        if state.is_terminal() or depth >= self.depth_limit:
            return state.utility("Demogorgon"), None
        
        v = INFINITY
        best_move = None
        
        for action in state.get_legal_moves():
            current_v, _ = self.ab_max_value(state.result(action), depth + 1, alpha, beta)
            
            if current_v < v:
                v = current_v
                best_move = action
                
            # Pruning condition: if v <= alpha, return v [4, 12]
            if v <= alpha:
                return v, best_move
            
            beta = min(beta, v)
            
        return v, best_move