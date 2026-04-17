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
            
            # Boundary validation for 5x5 to 8x8 grids [Requirement]
            if state.is_within_bounds(new_pos):
                # Update the character's position fluent [4, 5]
                new_state.update_character(agent['name'], pos=new_pos)
                
                # Check for hazards (Veins/Traps) which introduce nondeterminism [2, 6]
                GameRules._process_hazards(new_state, agent['name'], new_pos)

        elif action['type'] == 'TELEPORT':
            # Requirement: Teleportation enabled by 'hidden powers'
            if agent.get('has_powers', False):
                new_state.update_character(agent['name'], pos=action['destination'])
                # Teleportation consumes 'hidden powers' as an effect [7]
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
                random_pos = (random.randint(0, state.grid_size-1), 
                              random.randint(0, state.grid_size-1))
                state.update_character(agent_name, pos=random_pos)