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

            # Canonical boundary check lives on the state object
            if state.is_within_bounds(new_pos):
                if not state.is_impassable(new_pos):
                    legal_actions.append({'type': 'MOVE', 'direction': direction})

        # 2. Teleportation
        if state.has_hidden_powers(agent_name):
            for x in range(state.grid_size):
                for y in range(state.grid_size):
                    destination = (x, y)

                    if destination == current_pos:
                        continue

                    if not state.is_within_bounds(destination):
                        continue

                    if state.is_impassable(destination):
                        continue

                    legal_actions.append({'type': 'TELEPORT', 'destination': destination})

        return legal_actions

    @staticmethod
    def is_terminal(state):
        if MoveValidator._agent_caught_player(state):
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