class MoveValidator:
    """
    Implements Action Applicability (ACTIONS(s)) and Terminal Testing.
    Ensures that all moves conform to the grid constraints and character powers.
    """

    @staticmethod
    def get_legal_actions(state, agent_name):
        """
        Returns the set of actions applicable in the current state [1].
        Filters grid moves based on boundaries and character preconditions [4].
        """
        legal_actions = []
        directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        current_pos = state.get_position(agent_name)

        # 1. Standard Movement
        for direction in directions:
            new_pos = MoveValidator._calculate_new_position(current_pos, direction)
            
            # Boundary Precondition: Must be within 5x5 to 8x8 grid [Requirement]
            if MoveValidator._is_within_bounds(new_pos, state.grid_size):
                # Obstacle Precondition: Cannot move into impassable veins [Requirement]
                if not state.is_impassable(new_pos):
                    legal_actions.append({'type': 'MOVE', 'direction': direction})

        # 2. Special Ability: Teleportation [Requirement]
        # Precondition check: Character must possess 'hidden powers' [Requirement, 566]
        if state.has_hidden_powers(agent_name):
            # Teleportation allows for transitions to non-adjacent cells [5]
            for x in range(state.grid_size):
                for y in range(state.grid_size):
                    destination = (x, y)
                    # Cannot teleport to current spot or into impassable obstacles
                    if destination != current_pos and not state.is_impassable(destination):
                        legal_actions.append({'type': 'TELEPORT', 'destination': destination})

        return legal_actions

    @staticmethod
    def is_terminal(state):
        """
        Terminal test: determines if the game session has ended [3].
        """
        # Condition 1: An AI Agent monster has caught the Player (Eleven)
        if MoveValidator._agent_caught_player(state):
            return True

        # Condition 2: Eleven reached the escape goal state [71, Requirement]
        if state.player_at_goal():
            return True

        return False

    @staticmethod
    def _is_within_bounds(pos, grid_size):
        """Ensures coordinates stay within defined grid dimensions [Requirement]."""
        x, y = pos
        return 0 <= x < grid_size and 0 <= y < grid_size

    @staticmethod
    def _agent_caught_player(state):
        """Logic to determine if any monster occupies the same square as the player."""
        player_pos = state.get_position('Eleven')
        for monster in ['Demogorgon', 'Shadowmonster', 'Mindflayer']:
            if state.get_position(monster) == player_pos:
                return True
        return False

    @staticmethod
    def _calculate_new_position(pos, direction):
        """Helper to compute adjacent grid coordinates."""
        x, y = pos
        if direction == 'UP':    return (x, y - 1)
        if direction == 'DOWN':  return (x, y + 1)
        if direction == 'LEFT':  return (x - 1, y)
        if direction == 'RIGHT': return (x + 1, y)
        return (x, y)