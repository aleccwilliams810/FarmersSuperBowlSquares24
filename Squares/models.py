from django.db import models

# Create your models here.

class Participant(models.Model):
    name = models.CharField(max_length=100, unique=True)
    squares_pending = models.IntegerField(default=0)
    squares_purchased = models.IntegerField(default=0)
    purchase_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    def revert_purchased_squares(self, num_squares_to_revert):
        self.squares_purchased = max(0, self.squares_purchased - num_squares_to_revert)
        self.save(update_fields=['squares_purchased'])

    def revert_pending_squares(self, num_squares_to_revert):
        self.squares_pending = max(0, self.squares_pending - num_squares_to_revert)
        self.save(update_fields=['squares_pending'])

class GameScore(models.Model):
    kc_score = models.IntegerField(default=0)
    sf_score = models.IntegerField(default=0)
    quarter_finalized = models.CharField(max_length=4, blank=True, null=True)

    def __str__(self):
        last_game_score_id = GameScore.objects.last().id if GameScore.objects.exists() else 0
        if self.id:
            return f"GameScore {self.id - last_game_score_id}"
        else:
            return "New GameScore"

    class Meta:
        verbose_name_plural = 'GameScores'

class Square(models.Model):
    row = models.IntegerField()
    column = models.IntegerField()
    owner = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, blank=True)
    game_scores = models.ManyToManyField(GameScore, through='WinningQuarter', blank=True)

    class Meta:
        unique_together = ('row', 'column')

    def __str__(self):
        return f'Row: {self.row}, Column: {self.column}, Owner: {self.owner.name if self.owner else None}'
    

class WinningQuarter(models.Model):
    game_score = models.ForeignKey(GameScore, on_delete=models.CASCADE)
    square = models.ForeignKey(Square, on_delete=models.CASCADE)

    def __str__(self):
        return f'GameScore: {self.game_score.id} - Square: ({self.square.row}, {self.square.column})'
