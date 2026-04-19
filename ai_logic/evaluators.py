import math

def manhattan_distance(pos1, pos2):
    """
    Standard Manhattan (City Block) distance heuristic.
    Admissible for grid-based movement because it never overestimates
    the steps to the goal on a 4-direction grid.
    """
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

class StrangerThingsEvaluator:
    """
    Centralized evaluator for the game's search algorithms [1, 2].
    """

    @staticmethod
    def utility(state, agent_name):
        """
        Calculates utility for terminal states [5, 11].
        Standard AI scale: +1000 for win, -1000 for loss [12].
        """
        if state.is_win(agent_name):
            return 1000
        if state.is_loss(agent_name):
            return -1000
        return 0 # Draw or neutral end

    @staticmethod
    def static_evaluation(state, agent_name):
        """
        Estimates the quality of non-terminal states [2].
        Uses a weighted linear function to combine different features [13, 14].
        """
        # Feature extraction [15]
        agent_pos = state.get_position(agent_name)
        player_pos = state.get_closest_player_position(agent_pos)
        
        # 1. Proximity Feature: Closer to player is better for the AI [16]
        dist = manhattan_distance(agent_pos, player_pos)
        
        # 2. Obstacle Penalty: Being near traps/veins is dangerous [14]
        obstacle_penalty = 0
        neighbors = state.get_neighbors(agent_pos)
        for n in neighbors:
            if state.is_hazard(n): # Veins or Traps [Requirement]
                obstacle_penalty += 50

        # Weighted combination [13]
        # (Weight1 * proximity) + (Weight2 * hazard_safety)
        # Note: Weights used here are illustrative and not from the sources.
        return (-10 * dist) - obstacle_penalty

    @staticmethod
    def a_star_h(current_pos, goal_pos):
        """
        The heuristic h(n) specifically for Level 3 A* Search [6, 8].
        """
        return manhattan_distance(current_pos, goal_pos)