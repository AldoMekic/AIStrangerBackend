import math
import random

class MCTSNode:
    """
    Represents a node in the Monte Carlo Tree.
    Tracks visit counts and cumulative utility (value) [1, 6].
    """
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0.0 # Total reward accumulated from simulations [1]

    def is_fully_expanded(self, legal_moves):
        return len(self.children) == len(legal_moves)

class MindflayerAgent:
    """
    AI Agent representing the Mindflayer.
    Implements Level 4: Monte Carlo Tree Search (MCTS) with UCT [Requirement, 530].
    """
    def __init__(self, iterations=1000, exploration_constant=math.sqrt(2)):
        self.iterations = iterations
        self.exploration_constant = exploration_constant

    def get_action(self, game_state):
        """
        Decision entry point for the Mindflayer [Requirement].
        Executes four phases: Selection, Expansion, Simulation, and Backpropagation [1].
        """
        root = MCTSNode(state=game_state)
        
        for _ in range(self.iterations):
            # 1. Selection & 2. Expansion
            node = self.select_and_expand(root)
            # 3. Simulation (Rollout)
            reward = self.simulate(node.state)
            # 4. Backpropagation
            self.backpropagate(node, reward)
            
        # Return the action of the child that was visited most often [1]
        return self.best_child(root, c=0).action

    def select_and_expand(self, node):
        """
        Uses the UCT selection policy to traverse the tree until a 
        leaf node is reached that can be expanded [1, 2].
        """
        while not node.state.is_terminal():
            legal_moves = node.state.get_legal_moves()
            if not node.is_fully_expanded(legal_moves):
                return self.expand(node, legal_moves)
            else:
                node = self.best_child(node, self.exploration_constant)
        return node

    def expand(self, node, legal_moves):
        """
        Adds a new child node to the tree from the set of untried actions.
        """
        tried_actions = [child.action for child in node.children]
        untried_moves = [m for m in legal_moves if m not in tried_actions]
        
        action = random.choice(untried_moves)
        next_state = node.state.result(action)
        new_child = MCTSNode(state=next_state, parent=node, action=action)
        node.children.append(new_child)
        return new_child

    def simulate(self, state):
        """
        Rollout: From the new state, play a random game until a terminal 
        state is reached [1, 3]. This handles stochastic elements 
        like 'traps' by averaging their impact over many runs [4, 7].
        """
        current_rollout_state = state
        while not current_rollout_state.is_terminal():
            possible_moves = current_rollout_state.get_legal_moves()
            if not possible_moves:
                break
            # Random selection of moves (random walk) [3, 8]
            action = random.choice(possible_moves)
            current_rollout_state = current_rollout_state.result(action)
        
        # Return the final utility from the Mindflayer's perspective [9, 10]
        return current_rollout_state.utility("MINDFLAYER")

    def backpropagate(self, node, reward):
        """
        Updates the visit count and total value for every node along 
        the path back up to the root [1].
        """
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    def best_child(self, node, c):
        """
        Upper Confidence bounds on Trees (UCT) selection formula [1, 2].
        Balances exploitation (average value) and exploration (visiting less-tried branches).
        """
        best_score = -math.inf
        best_children = []
        
        for child in node.children:
            # Exploitation: current average utility
            exploitation = child.value / child.visits
            # Exploration: bonus for nodes with few visits relative to parent
            exploration = c * math.sqrt(math.log(node.visits) / child.visits)
            
            score = exploitation + exploration
            
            if score > best_score:
                best_score = score
                best_children = [child]
            elif score == best_score:
                best_children.append(child)
                
        return random.choice(best_children)