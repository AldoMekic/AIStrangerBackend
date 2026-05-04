from rest_framework import serializers
from .models import Game, Character, Obstacle
from .state import GameState


class CharacterSerializer(serializers.ModelSerializer):
    """
    Serializes character data including grid coordinates and special powers.
    """
    class Meta:
        model = Character
        fields = ['id', 'name', 'x_pos', 'y_pos', 'has_powers', 'is_ai', 'stuck']


class ObstacleSerializer(serializers.ModelSerializer):
    """
    Serializes veins and traps to be rendered on the grid.
    """
    class Meta:
        model = Obstacle
        fields = ['id', 'obstacle_type', 'x_pos', 'y_pos']


class GameSerializer(serializers.ModelSerializer):
    characters = CharacterSerializer(many=True, read_only=True)
    obstacles = ObstacleSerializer(many=True, read_only=True)
    goal_position = serializers.SerializerMethodField()
    available_actions = serializers.SerializerMethodField()
    can_teleport = serializers.SerializerMethodField()
    teleport_targets = serializers.SerializerMethodField()
    last_event = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id',
            'grid_size',
            'game_mode',
            'difficulty_level',
            'current_turn',
            'is_over',
            'winner',
            'created_at',
            'goal_x',
            'goal_y',
            'goal_position',
            'available_actions',
            'can_teleport',
            'teleport_targets',
            'characters',
            'obstacles',
            'last_event',
        ]

    def get_goal_position(self, obj):
        return [obj.goal_x, obj.goal_y]

    def get_available_actions(self, obj):
        state = GameState.from_game(obj)

        if state.is_over:
            return []

        actions = state.get_legal_moves()

        normalized_actions = []
        for action in actions:
            if action["type"] == "MOVE":
                normalized_actions.append({
                    "type": "MOVE",
                    "direction": action["direction"],
                })

            elif action["type"] == "TELEPORT":
                destination = action["destination"]
                normalized_actions.append({
                    "type": "TELEPORT",
                    "destination": [destination[0], destination[1]],
                })

        return normalized_actions

    def get_can_teleport(self, obj):
        state = GameState.from_game(obj)

        if state.is_over:
            return False

        active_name = state.current_turn

        if active_name not in state.characters:
            return False

        return any(
            action["type"] == "TELEPORT"
            for action in state.get_legal_moves()
        )

    def get_teleport_targets(self, obj):
        state = GameState.from_game(obj)

        if state.is_over:
            return []

        targets = []

        for action in state.get_legal_moves():
            if action["type"] == "TELEPORT":
                destination = action["destination"]
                targets.append([destination[0], destination[1]])

        return targets
    
    def get_last_event(self, obj):
        return self.context.get("last_event")


class ActionSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["MOVE", "TELEPORT"])
    direction = serializers.ChoiceField(
        choices=["UP", "DOWN", "LEFT", "RIGHT"],
        required=False,
    )
    destination = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=2,
        max_length=2,
        required=False,
    )

    def validate(self, data):
        action_type = data.get("type")

        if action_type == "MOVE":
            if "direction" not in data:
                raise serializers.ValidationError({
                    "direction": "Direction is required for MOVE actions."
                })

            return {
                "type": "MOVE",
                "direction": data["direction"],
            }

        if action_type == "TELEPORT":
            if "destination" not in data:
                raise serializers.ValidationError({
                    "destination": "Destination is required for TELEPORT actions."
                })

            destination = data["destination"]

            return {
                "type": "TELEPORT",
                "destination": (destination[0], destination[1]),
            }

        raise serializers.ValidationError("Unsupported action type.")