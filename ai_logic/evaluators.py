def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


class StrangerThingsEvaluator:
    @staticmethod
    def utility(state, agent_name):
        if state.is_win(agent_name):
            return 1000
        if state.is_loss(agent_name):
            return -1000
        return 0

    @staticmethod
    def static_evaluation(state, agent_name):
        agent_pos = state.get_position(agent_name)
        player_pos = state.get_closest_player_position(agent_pos)

        distance_score = -10 * manhattan_distance(agent_pos, player_pos)
        corner_score = StrangerThingsEvaluator.cornering_score(state, player_pos)

        if agent_name == "DEMOGORGON":
            # Level 1 and 2: mainly chase the player.
            return distance_score

        if agent_name == "SHADOWMONSTER":
            # Level 3: prefer forcing the player near obstacles.
            return corner_score - 3 * manhattan_distance(agent_pos, player_pos)

        if agent_name == "MINDFLAYER":
            # Level 4: combine chasing and cornering.
            return distance_score + corner_score

        return distance_score

    @staticmethod
    def cornering_score(state, player_pos):
        """
        Higher score means the player has fewer safe escape options
        and is closer to hazards.
        """
        score = 0

        safe_escape_count = 0

        for neighbor in state.get_neighbors(player_pos):
            if state.is_impassable(neighbor):
                score += 25
                continue

            if state.is_hazard(neighbor):
                score += 20

            if not state.is_occupied(neighbor):
                safe_escape_count += 1

        score += (4 - safe_escape_count) * 30

        return score

    @staticmethod
    def a_star_h(current_pos, goal_pos):
        return manhattan_distance(current_pos, goal_pos)