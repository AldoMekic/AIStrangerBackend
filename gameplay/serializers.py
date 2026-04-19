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
    Serializes 'veins' and 'traps' to be rendered as animations on the grid.
    """
    class Meta:
        model = Obstacle
        fields = ['id', 'obstacle_type', 'x_pos', 'y_pos']

class GameSerializer(serializers.ModelSerializer):
    """
    The primary serializer representing the complete State Space of the game.
    Nests characters and obstacles to provide a full snapshot of the current environment.
    """
    characters = CharacterSerializer(many=True, read_only=True)
    obstacles = ObstacleSerializer(many=True, read_only=True)

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
            'characters',
            'obstacles'
        ]