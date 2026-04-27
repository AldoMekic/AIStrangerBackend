import random

class GameRules:
    """
    Implements the 'physics' of the game environment.
    Contains the formal Transition Model: RESULT(s, a) [1, 2].
    """

    @staticmethod
    def result(state, action):
        """
        Returns the state that results from doing action 'a' in state 's'.
        Handles deterministic movement and nondeterministic hazards [1, 2].
        """
        # Create a deep copy of the state to avoid modifying the current one
        # This is essential for AI 'search' trees [3]
        new_state = state.clone()
        agent = state.get_active_character()

        if action['type'] == 'MOVE':
            new_pos = GameRules._calculate_new_position(agent['pos'], action['direction'])

            if new_state.can_move_to(new_pos, agent['name']):
                new_state.update_character(agent['name'], pos=new_pos)
                GameRules._process_hazards(new_state, agent['name'], new_pos)

        elif action['type'] == 'TELEPORT':
            destination = action.get('destination')

            # Requirement: Teleportation enabled by hidden powers
            if agent.get('has_powers', False) and new_state.is_valid_teleport_destination(
                destination,
                agent['name'],
            ):
                new_state.update_character(agent['name'], pos=destination)
                # Teleportation consumes hidden powers
                new_state.update_character(agent['name'], has_powers=False)

        # Update the turn fluent to the next player [8, 9]
        new_state.advance_turn()
        return new_state

    @staticmethod
    def _calculate_new_position(current_pos, direction):
        """Helper to compute coordinates on the grid."""
        x, y = current_pos
        if direction == 'UP':    return (x, y - 1)
        if direction == 'DOWN':  return (x, y + 1)
        if direction == 'LEFT':  return (x - 1, y)
        if direction == 'RIGHT': return (x + 1, y)
        return (x, y)
    

    @staticmethod
    def _get_safe_random_position(state, agent_name):
        """
        Returns a random valid relocation cell for trap effects.

        Excludes:
        - impassable cells
        - occupied cells (except the moving character's current cell)
        - the goal tile
        """
        valid_positions = []
        current_pos = state.get_position(agent_name)

        for x in range(state.grid_size):
            for y in range(state.grid_size):
                candidate = (x, y)

                if not state.is_within_bounds(candidate):
                    continue

                if state.is_impassable(candidate):
                    continue

                if state.is_forbidden_relocation_cell(candidate):
                    continue

                if state.is_occupied(candidate, exclude_agent=agent_name):
                    continue

                # avoid pointless relocation to same spot
                if candidate == current_pos:
                    continue

                valid_positions.append(candidate)

        if not valid_positions:
            return None

        return random.choice(valid_positions)

    @staticmethod
    def _process_hazards(state, agent_name, pos):
        """
        Implements the 'Erratic' environment logic [10].
        Veins and Traps result in nondeterministic state transitions [2].
        """
        hazard = state.get_obstacle_at(pos)
        
        if hazard == 'VEIN':
            # Effect: The character is 'trapped' and loses their next turn [Requirement]
            state.set_character_status(agent_name, 'stuck', True)
        
        elif hazard == 'TRAP':
            # Nondeterministic outcome: 50% chance of random relocation [2, 11]
            if random.random() < 0.5:
                safe_pos = GameRules._get_safe_random_position(state, agent_name)
                if safe_pos is not None:
                    state.update_character(agent_name, pos=safe_pos)
    
    
    @staticmethod
    def _is_capture_move(state, agent_name, destination):
        """
        A move is a capture if the destination is occupied by an enemy.
        """
        return state.is_enemy_occupied(destination, agent_name)