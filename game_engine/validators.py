class MoveValidator:
    """
    Implements action applicability and terminal testing.
    Uses the state object as the single source of truth for boundary validity.
    """

    @staticmethod
    def get_legal_actions(state, agent_name):
        legal_actions = []
        directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        current_pos = state.get_position(agent_name)

        # 1. Standard movement
        for direction in directions:
            new_pos = MoveValidator._calculate_new_position(current_pos, direction)

            if state.can_move_to(new_pos, agent_name):
                legal_actions.append({'type': 'MOVE', 'direction': direction})

        # 2. Teleportation
        if state.has_hidden_powers(agent_name):
            teleport_radius = 2
            teleport_destinations = MoveValidator._get_teleport_candidates(
                state,
                agent_name,
                current_pos,
                teleport_radius,
            )

            for destination in teleport_destinations:
                legal_actions.append({'type': 'TELEPORT', 'destination': destination})

        return legal_actions

    @staticmethod
    def is_terminal(state):
        if state.game_mode == "PVA" and MoveValidator._agent_caught_player(state):
            return True

        if state.player_at_goal():
            return True

        return False

    @staticmethod
    def _agent_caught_player(state):
        player_pos = state.get_position('ELEVEN')
        for monster in ['DEMOGORGON', 'SHADOWMONSTER', 'MINDFLAYER']:
            if monster in state.characters and state.get_position(monster) == player_pos:
                return True
        return False

    @staticmethod
    def _calculate_new_position(pos, direction):
        x, y = pos
        if direction == 'UP':
            return (x, y - 1)
        if direction == 'DOWN':
            return (x, y + 1)
        if direction == 'LEFT':
            return (x - 1, y)
        if direction == 'RIGHT':
            return (x + 1, y)
        return (x, y)
    
    @staticmethod
    def _get_teleport_candidates(state, agent_name, current_pos, radius=2, max_candidates=8):
        """
        Generate a constrained set of teleport destinations.

        Uses the same safety rules as runtime teleport validation and
        trap relocation safety:
        - within Manhattan radius
        - not impassable
        - not occupied
        - not forbidden (for example, the goal tile)
        - not the current position
        """
        candidates = []

        for x in range(state.grid_size):
            for y in range(state.grid_size):
                destination = (x, y)

                if MoveValidator._manhattan_distance(current_pos, destination) > radius:
                    continue

                if not state.is_valid_teleport_destination(destination, agent_name):
                    continue

                candidates.append(destination)

        candidates.sort(key=lambda pos: (
            MoveValidator._manhattan_distance(current_pos, pos),
            pos[1],
            pos[0],
        ))

        return candidates[:max_candidates]

    @staticmethod
    def _manhattan_distance(pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])