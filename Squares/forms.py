from django import forms
from .models import Participant, GameScore

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['name']


class PurchaseForm(forms.Form):
    num_squares = forms.IntegerField(label='Number of Squares', min_value=1, max_value=10)


class RevertSquaresForm(forms.Form):
    REVERT_CHOICES = [
        ('purchased', 'Purchaed Squares'),
        ('pending', 'Pending Squares'),
    ]
    num_squares_to_revert = forms.IntegerField(min_value= 1, label='Number of Squares to Revert')
    square_type = forms.ChoiceField(choices=REVERT_CHOICES, label='Type of Squares to Revert')

class ScoreUpdateForm(forms.ModelForm):
    class Meta:
        model = GameScore
        fields = ['kc_score', 'sf_score', 'quarter_finalized']

    def __init__(self, *args, **kwargs):
        super(ScoreUpdateForm, self).__init__(*args, **kwargs)
        self.fields['quarter_finalized'].choices = [('', '-----'), ('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Game', 'Game')]
