from rest_framework import serializers
from .models import Game, Character, Obstacle


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
            'characters',
            'obstacles',
        ]

    def get_goal_position(self, obj):
        return [obj.goal_x, obj.goal_y]