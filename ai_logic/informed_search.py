import heapq


class Node:
    """
    Data structure representing a node in the search tree.
    For A*, state is a position tuple: (x, y).
    """
    def __init__(self, state, parent=None, action=None, path_cost=0, heuristic=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.g = path_cost
        self.h = heuristic
        self.f = self.g + self.h

    def __lt__(self, other):
        return self.f < other.f


class ShadowmonsterAgent:
    """
    AI Agent representing the Shadowmonster.
    Implements Level 3: A* Search.
    """

    def get_action(self, game_state):
        return self.a_star_search(game_state)

    def a_star_search(self, problem):
        start_state = problem.get_current_state()
        goal_state = problem.get_player_location()

        start_node = Node(
            state=start_state,
            path_cost=0,
            heuristic=self.manhattan_heuristic(start_state, goal_state),
        )

        frontier = []
        heapq.heappush(frontier, start_node)

        best_cost = {start_state: 0}
        explored = set()

        while frontier:
            node = heapq.heappop(frontier)

            if node.state in explored:
                continue

            if problem.is_ai_target(node.state):
                return self.solution_path(node)

            explored.add(node.state)

            for action in problem.get_legal_moves(node.state):
                result_state = problem.result(node.state, action)

                # problem.result(...) returns a GameState, so extract the AI's new position.
                child_position = result_state.get_current_state()

                new_cost = node.g + problem.step_cost(node.state, action)

                if child_position in explored:
                    continue

                if child_position not in best_cost or new_cost < best_cost[child_position]:
                    best_cost[child_position] = new_cost

                    child_node = Node(
                        state=child_position,
                        parent=node,
                        action=action,
                        path_cost=new_cost,
                        heuristic=self.manhattan_heuristic(child_position, goal_state),
                    )

                    heapq.heappush(frontier, child_node)

        return None

    def manhattan_heuristic(self, state, goal):
        return abs(state[0] - goal[0]) + abs(state[1] - goal[1])

    def solution_path(self, node):
        actions = []

        while node.parent is not None:
            actions.append(node.action)
            node = node.parent

        return actions[-1] if actions else None