from django.db import models

class Game(models.Model):
    """
    Represents an active or saved game instance.
    Stores the configuration and high-level environment parameters.
    """
    GRID_SIZE_CHOICES = [(i, f"{i}x{i}") for i in range(5, 9)]
    MODE_CHOICES = [('PVP', 'Player vs Player'), ('PVA', 'Player vs AI')]
    LEVEL_CHOICES = [
        (1, 'Level 1: Minimax (Demogorgon)'),
        (2, 'Level 2: Alpha-Beta (Demogorgon)'),
        (3, 'Level 3: A* Search (Shadowmonster)'),
        (4, 'Level 4: MCTS (Mindflayer)'),
    ]

    WINNER_CHOICES = [
        ('ELEVEN', 'Eleven'),
        ('DEMOGORGON', 'Demogorgon'),
        ('SHADOWMONSTER', 'Shadowmonster'),
        ('MINDFLAYER', 'Mindflayer'),
    ]

    grid_size = models.IntegerField(choices=GRID_SIZE_CHOICES, default=5)
    game_mode = models.CharField(max_length=3, choices=MODE_CHOICES, default='PVA')
    difficulty_level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    current_turn = models.CharField(max_length=50, default='ELEVEN')
    is_over = models.BooleanField(default=False)
    winner = models.CharField(
        max_length=50,
        choices=WINNER_CHOICES,
        null=True,
        blank=True,
        default=None,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game {self.id} ({self.get_game_mode_display()})"

class Character(models.Model):
    """
    Tracks the state of every agent in the environment [3].
    Represents the 'factored' attributes of players and AI agents [2].
    """
    CHARACTER_TYPES = [
        ('ELEVEN', 'Eleven'),
        ('DEMOGORGON', 'Demogorgon'),
        ('SHADOWMONSTER', 'Shadowmonster'),
        ('MINDFLAYER', 'Mindflayer'),
    ]

    game = models.ForeignKey(Game, related_name='characters', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, choices=CHARACTER_TYPES)
    x_pos = models.IntegerField() # Horizontal coordinate on the grid
    y_pos = models.IntegerField() # Vertical coordinate on the grid
    has_powers = models.BooleanField(default=False) # Enables teleportation [Requirement]
    is_ai = models.BooleanField(default=False)
    stuck = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} at ({self.x_pos}, {self.y_pos})"

class Obstacle(models.Model):
    """
    Represents random 'veins' and 'traps' in the Upside Down [Requirement].
    These elements introduce nondeterminism into the state space [4].
    """
    OBSTACLE_TYPES = [('VEIN', 'Vein'), ('TRAP', 'Trap')]

    game = models.ForeignKey(Game, related_name='obstacles', on_delete=models.CASCADE)
    obstacle_type = models.CharField(max_length=10, choices=OBSTACLE_TYPES)
    x_pos = models.IntegerField()
    y_pos = models.IntegerField()

    def __str__(self):
        return f"{self.obstacle_type} at ({self.x_pos}, {self.y_pos})"