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
        A* algorithm with best-cost tracking.

        Prevents repeated states from being expanded through more expensive paths.
        """
        start_state = problem.get_current_state()
        goal_state = problem.get_player_location()
        h_start = self.manhattan_heuristic(start_state, goal_state)

        start_node = Node(state=start_state, path_cost=0, heuristic=h_start)

        frontier = []
        heapq.heappush(frontier, start_node)

        best_cost = {
            start_state: 0
        }

        explored = set()

        while frontier:
            node = heapq.heappop(frontier)

            if node.state in explored:
                continue

            if problem.is_ai_target(node.state):
                return self.solution_path(node)

            explored.add(node.state)

            for action in problem.get_legal_moves(node.state):
                child_state = problem.result(node.state, action)
                new_cost = node.g + problem.step_cost(node.state, action)

                if child_state in explored:
                    continue

                if child_state not in best_cost or new_cost < best_cost[child_state]:
                    best_cost[child_state] = new_cost

                    h_cost = self.manhattan_heuristic(child_state, goal_state)
                    child_node = Node(
                        state=child_state,
                        parent=node,
                        action=action,
                        path_cost=new_cost,
                        heuristic=h_cost,
                    )

                    heapq.heappush(frontier, child_node)

        return None

    def manhattan_heuristic(self, state, goal):
        """
        Manhattan distance (City Block distance) heuristic.
        Admissible because it never overestimates the steps to the goal
        on a 4-direction grid.
        """
        return abs(state[0] - goal[0]) + abs(state[1] - goal[1])

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