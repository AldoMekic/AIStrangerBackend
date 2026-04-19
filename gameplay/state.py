from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ai_logic.evaluators import StrangerThingsEvaluator
from game_engine.rules import GameRules
from game_engine.validators import MoveValidator

Position = Tuple[int, int]


@dataclass
class CharacterState:
    name: str
    pos: Position
    has_powers: bool = False
    is_ai: bool = False
    stuck: bool = False


@dataclass
class GameState:
    grid_size: int
    game_mode: str
    difficulty_level: int
    current_turn: str
    is_over: bool = False
    winner: Optional[str] = None
    goal_position: Optional[Position] = None
    characters: Dict[str, CharacterState] = field(default_factory=dict)
    obstacles: Dict[Position, str] = field(default_factory=dict)

    CHARACTER_NAME_MAP = {
        "ELEVEN": "ELEVEN",
        "Eleven": "ELEVEN",
        "eleven": "ELEVEN",
        "PLAYER1": "ELEVEN",
        "Player1": "ELEVEN",
        "player1": "ELEVEN",
        "DEMOGORGON": "DEMOGORGON",
        "Demogorgon": "DEMOGORGON",
        "demogorgon": "DEMOGORGON",
        "SHADOWMONSTER": "SHADOWMONSTER",
        "Shadowmonster": "SHADOWMONSTER",
        "shadowmonster": "SHADOWMONSTER",
        "MINDFLAYER": "MINDFLAYER",
        "Mindflayer": "MINDFLAYER",
        "mindflayer": "MINDFLAYER",
    }

    AI_BY_LEVEL = {
        1: "DEMOGORGON",
        2: "DEMOGORGON",
        3: "SHADOWMONSTER",
        4: "MINDFLAYER",
    }

    @classmethod
    def normalize_name(cls, name: str) -> str:
        if not isinstance(name, str):
            return name
        return cls.CHARACTER_NAME_MAP.get(name, name.upper())

    @classmethod
    def from_game(cls, game) -> "GameState":
        characters: Dict[str, CharacterState] = {}

        for ch in game.characters.all():
            normalized = cls.normalize_name(ch.name)
            characters[normalized] = CharacterState(
                name=normalized,
                pos=(ch.x_pos, ch.y_pos),
                has_powers=ch.has_powers,
                is_ai=ch.is_ai,
                stuck=ch.stuck,
            )

        obstacles: Dict[Position, str] = {}
        for ob in game.obstacles.all():
            obstacles[(ob.x_pos, ob.y_pos)] = ob.obstacle_type

        return cls(
            grid_size=game.grid_size,
            game_mode=game.game_mode,
            difficulty_level=game.difficulty_level,
            current_turn=cls.normalize_name(game.current_turn),
            is_over=game.is_over,
            winner=getattr(game, "winner", None),
            goal_position=(game.grid_size - 1, game.grid_size - 1),
            characters=characters,
            obstacles=obstacles,
        )

    def apply_to_game(self, game) -> None:
        game.current_turn = self.current_turn
        game.is_over = self.is_over

        if hasattr(game, "winner"):
            game.winner = self.winner

        update_fields = ["current_turn", "is_over"]
        if hasattr(game, "winner"):
            update_fields.append("winner")

        game.save(update_fields=update_fields)

        for ch_model in game.characters.all():
            normalized = self.normalize_name(ch_model.name)
            if normalized not in self.characters:
                continue

            ch_state = self.characters[normalized]
            ch_model.x_pos = ch_state.pos[0]
            ch_model.y_pos = ch_state.pos[1]
            ch_model.has_powers = ch_state.has_powers
            ch_model.is_ai = ch_state.is_ai
            ch_model.stuck = ch_state.stuck
            ch_model.save(update_fields=["x_pos", "y_pos", "has_powers", "is_ai", "stuck"])

    # ---------- METHODS REQUIRED BY rules.py ----------

    def clone(self) -> "GameState":
        """
        Required by GameRules.result() and all tree-search algorithms.
        """
        return copy.deepcopy(self)

    def get_active_character(self) -> Dict[str, Any]:
        """
        Required by GameRules.result().
        Returns the active character in the dictionary shape expected by rules.py.
        """
        active_name = self.normalize_name(self.current_turn)
        ch = self.characters[active_name]
        return {
            "name": ch.name,
            "pos": ch.pos,
            "has_powers": ch.has_powers,
            "is_ai": ch.is_ai,
            "stuck": ch.stuck,
        }

    def is_within_bounds(self, pos) -> bool:
        x, y = pos
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size

    def update_character(
        self,
        agent_name: str,
        *,
        pos: Optional[Position] = None,
        has_powers: Optional[bool] = None,
        is_ai: Optional[bool] = None,
    ) -> None:
        """
        Required by GameRules.result().
        """
        normalized = self.normalize_name(agent_name)
        ch = self.characters[normalized]

        if pos is not None:
            ch.pos = pos
        if has_powers is not None:
            ch.has_powers = has_powers
        if is_ai is not None:
            ch.is_ai = is_ai

    def advance_turn(self) -> None:
        """
        Required by GameRules.result().
        Uses canonical character identity values only.
        """
        if self.game_mode == "PVA":
            ai_name = self.AI_BY_LEVEL.get(self.difficulty_level, "DEMOGORGON")

            if self.current_turn == "ELEVEN":
                next_turn = ai_name
            else:
                next_turn = "ELEVEN"

            if next_turn in self.characters and self.characters[next_turn].stuck:
                self.characters[next_turn].stuck = False
                next_turn = "ELEVEN" if next_turn != "ELEVEN" else ai_name

            self.current_turn = next_turn
            return

        self.current_turn = "ELEVEN"

    def get_obstacle_at(self, pos: Position) -> Optional[str]:
        """
        Required by GameRules._process_hazards().
        """
        return self.obstacles.get(pos)

    def set_character_status(self, agent_name: str, status_name: str, value: bool) -> None:
        """
        Required by GameRules._process_hazards().
        """
        normalized = self.normalize_name(agent_name)
        ch = self.characters[normalized]

        if status_name == "stuck":
            ch.stuck = value

    # ---------- SUPPORT METHODS USED BY validators.py / AI ----------

    def get_position(self, agent_name: str) -> Position:
        normalized = self.normalize_name(agent_name)
        return self.characters[normalized].pos

    def is_stuck(self, agent_name: str) -> bool:
        normalized = self.normalize_name(agent_name)
        return self.characters[normalized].stuck

    def has_hidden_powers(self, agent_name: str) -> bool:
        normalized = self.normalize_name(agent_name)
        return self.characters[normalized].has_powers

    def is_hazard(self, pos: Position) -> bool:
        return pos in self.obstacles

    def is_impassable(self, pos: Position) -> bool:
        return self.obstacles.get(pos) == "VEIN"

    def get_neighbors(self, pos: Position) -> List[Position]:
        x, y = pos
        candidates = [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]
        return [p for p in candidates if self.is_within_bounds(p)]

    def get_legal_moves(self, node_state: Optional[Position] = None):
        active_name = self.current_turn

        if self.is_stuck(active_name):
            return []

        if node_state is None:
            return MoveValidator.get_legal_actions(self, active_name)

        temp = self.clone()
        temp.update_character(active_name, pos=node_state)
        return MoveValidator.get_legal_actions(temp, active_name)

    def result(self, *args):
        if len(args) == 1:
            action = args[0]
            return GameRules.result(self, action)

        if len(args) == 2:
            node_state, action = args
            temp = self.clone()
            temp.update_character(temp.current_turn, pos=node_state)
            return GameRules.result(temp, action)

        raise TypeError("result() expects either (action) or (node_state, action)")

    def is_terminal(self) -> bool:
        return MoveValidator.is_terminal(self) or self.is_over

    def player_at_goal(self) -> bool:
        if "ELEVEN" not in self.characters or self.goal_position is None:
            return False
        return self.characters["ELEVEN"].pos == self.goal_position

    def get_closest_player_position(self, reference_pos: Position) -> Position:
        return self.get_position("ELEVEN")

    def get_current_state(self) -> Position:
        return self.get_position(self.current_turn)

    def get_player_location(self) -> Position:
        return self.get_position("ELEVEN")

    def is_goal(self, pos: Position) -> bool:
        return pos == self.get_player_location()

    def step_cost(self, _state: Position, _action: Dict[str, Any]) -> int:
        return 1

    def is_win(self, agent_name: str) -> bool:
        normalized = self.normalize_name(agent_name)

        if normalized == "ELEVEN":
            return self.player_at_goal()

        if normalized in {"DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"}:
            return (
                normalized in self.characters
                and self.get_position(normalized) == self.get_position("ELEVEN")
            )

        return False

    def is_loss(self, agent_name: str) -> bool:
        normalized = self.normalize_name(agent_name)

        if normalized == "ELEVEN":
            for enemy in ("DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"):
                if enemy in self.characters and self.get_position(enemy) == self.get_position("ELEVEN"):
                    return True
            return False

        if normalized in {"DEMOGORGON", "SHADOWMONSTER", "MINDFLAYER"}:
            return self.player_at_goal()

        return False

    def utility(self, agent_name: str) -> int:
        normalized = self.normalize_name(agent_name)

        if self.is_terminal():
            return StrangerThingsEvaluator.utility(self, normalized)

        return StrangerThingsEvaluator.static_evaluation(self, normalized)
    
    def is_occupied(self, pos, exclude_agent=None) -> bool:
        """
        Returns True if any character occupies the given cell.

        exclude_agent:
            optional canonical or legacy name to ignore during the check.
        """
        normalized_exclude = self.normalize_name(exclude_agent) if exclude_agent else None

        for name, ch in self.characters.items():
            if normalized_exclude is not None and name == normalized_exclude:
                continue
            if ch.pos == pos:
                return True
        return False

    def is_forbidden_relocation_cell(self, pos) -> bool:
        """
        Cells that trap relocation is not allowed to target.
        """
        if self.goal_position is not None and pos == self.goal_position:
            return True
        return False