import heapq
from ai_logic.evaluators import manhattan_distance, StrangerThingsEvaluator


class Node:
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
    Level 3 strategy:
    Uses A* to move toward a strategic position near the player.
    The target is selected to reduce the player's escape options and
    pressure them toward veins/traps.
    """

    def get_action(self, game_state):
        return self.a_star_search(game_state)

    def a_star_search(self, problem):
        start_state = problem.get_current_state()
        goal_state = self.choose_cornering_target(problem)

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

            if node.state == goal_state or problem.is_ai_target(node.state):
                return self.solution_path(node)

            explored.add(node.state)

            for action in problem.get_legal_moves(node.state):
                result_state = problem.result(node.state, action)
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

    def choose_cornering_target(self, state):
        ai_pos = state.get_current_state()
        player_pos = state.get_player_location()

        candidate_targets = []

        # If capture is already possible, chase directly.
        if manhattan_distance(ai_pos, player_pos) <= 1:
            return player_pos

        for pos in state.get_neighbors(player_pos):
            if not state.is_within_bounds(pos):
                continue

            if state.is_impassable(pos):
                continue

            if state.is_occupied(pos):
                continue

            corner_score = StrangerThingsEvaluator.cornering_score(state, pos)
            distance_penalty = manhattan_distance(ai_pos, pos)

            score = corner_score - distance_penalty

            candidate_targets.append((score, pos))

        if not candidate_targets:
            return player_pos

        candidate_targets.sort(reverse=True, key=lambda item: item[0])
        return candidate_targets[0][1]

    def manhattan_heuristic(self, state, goal):
        return abs(state[0] - goal[0]) + abs(state[1] - goal[1])

    def solution_path(self, node):
        actions = []

        while node.parent is not None:
            actions.append(node.action)
            node = node.parent

        return actions[-1] if actions else None