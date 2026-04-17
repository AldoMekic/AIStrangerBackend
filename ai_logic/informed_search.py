import heapq

class Node:
    """
    Data structure representing a node in the search tree [5].
    Contains the state, parent pointer, action taken, and path costs [5, 6].
    """
    def __init__(self, state, parent=None, action=None, path_cost=0, heuristic=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = path_cost  # Cost from the start node to this node [5]
        self.h = heuristic  # Estimated cost from this node to the goal [7]
        self.f = self.g + self.h  # Total estimated solution cost [2]

    # Required for the priority queue to order nodes by their f-score [8, 9]
    def __lt__(self, other):
        return self.f < other.f

class ShadowmonsterAgent:
    """
    AI Agent representing the Shadowmonster.
    Implements Level 3: A* Search [Requirement].
    """

    def get_action(self, game_state):
        """
        Decision entry point for the Shadowmonster [Requirement].
        """
        return self.a_star_search(game_state)

    def a_star_search(self, problem):
        """
        A* algorithm: Minimizes the total estimated solution cost [2].
        Uses a priority queue for the frontier and an explored set for efficiency [8, 10].
        """
        # 1. Initialize start node and goal information
        start_state = problem.get_current_state()
        goal_state = problem.get_player_location()
        h_start = self.manhattan_heuristic(start_state, goal_state)
        
        start_node = Node(state=start_state, path_cost=0, heuristic=h_start)
        
        # 2. Frontier as a Priority Queue (Min-Heap) [8, 9]
        frontier = []
        heapq.heappush(frontier, start_node)
        
        # 3. Explored set to handle repeated states in the grid [3]
        explored = set()

        while frontier:
            # 4. Pop the node with the lowest f(n) from the frontier [9, 10]
            node = heapq.heappop(frontier)
            
            # 5. Goal Test: Check if we have reached the player's position [11, 12]
            if problem.is_goal(node.state):
                return self.solution_path(node)
            
            # 6. Add node to explored set [3, 13]
            explored.add(node.state)
            
            # 7. Expand the node by generating child nodes [14, 15]
            for action in problem.get_legal_moves(node.state):
                # Transition model: RESULT(s, a) [16, 17]
                child_state = problem.result(node.state, action)
                
                if child_state not in explored:
                    # Path cost: g(child) = g(parent) + step_cost [6]
                    g_cost = node.g + problem.step_cost(node.state, action)
                    h_cost = self.manhattan_heuristic(child_state, goal_state)
                    child_node = Node(child_state, node, action, g_cost, h_cost)
                    
                    # Add to frontier if not already present with a better cost [18]
                    heapq.heappush(frontier, child_node)
                    
        return None # No path found [19]

    def manhattan_heuristic(self, state, goal):
        """
        Manhattan distance (City Block distance) heuristic [20].
        Admissible because it never overestimates the steps to the goal on a grid [20, 21].
        """
        # d = |x1 - x2| + |y1 - y2|
        return abs(state - goal) + abs(state[22] - goal[22])

    def solution_path(self, node):
        """
        Extracts the sequence of actions by following parent pointers [6].
        Returns the first action the Shadowmonster should take this turn.
        """
        actions = []
        while node.parent is not None:
            actions.append(node.action)
            node = node.parent
        # The first action to take is at the end of the reversed list
        return actions[-1] if actions else None