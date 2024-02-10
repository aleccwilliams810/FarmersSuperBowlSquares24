from django.shortcuts import render, redirect
from .forms import ParticipantForm, PurchaseForm
from django.db.models import Sum, F
from .models import Participant, Square, GameScore, WinningQuarter
from django.http import HttpResponse



#views

def dickroll(request):
    return render(request, 'Squares/dickroll.html')

def register_participant(request):
    if request.method == 'POST':
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save()
            response = redirect('home')
            response.set_cookie('participant_id', participant.id, max_age=31536000)
            return response
    else:
        form = ParticipantForm()
    return render(request,'Squares/register.html',{'form': form})


def home(request):
    participant_id = request.COOKIES.get('participant_id')
    context = {}
    total_squares = 100
    cap_enabled = True
    num_participants = 10

    purchased_squares_total = Participant.objects.aggregate(total_purchased=Sum('squares_purchased'))['total_purchased'] or 0
    pending_squares_total = Participant.objects.aggregate(total_pending=Sum('squares_pending'))['total_pending'] or 0
    remaining_squares = total_squares - (purchased_squares_total + pending_squares_total)

    participant = Participant.objects.filter(id=participant_id).first()
    if participant:
        context['participant_name'] = participant.name

        if cap_enabled:
            initial_cap = total_squares // num_participants
        else:
            initial_cap = remaining_squares

        if request.method == 'POST':
            form = PurchaseForm(request.POST)
            if form.is_valid():
                num_squares = form.cleaned_data['num_squares']

                if num_squares <= initial_cap and num_squares <= remaining_squares:
                    participant.squares_pending += num_squares
                    participant.purchase_complete = False
                    participant.save()
                    remaining_squares -= num_squares
        else:
            form = PurchaseForm(initial={'num_squares': initial_cap})

        winners_info = WinningQuarter.objects.select_related('square__owner', 'game_score').filter(
            game_score__quarter_finalized__isnull=False
        ).annotate(
            quarter = F('game_score__quarter_finalized'),
            participant_id = F('square__owner__id')
        ).values('quarter', 'participant_id').order_by('quarter')

        winners_by_quarter = {}
        for winner in winners_info:
            quarter = winner['quarter']
            if quarter not in winners_by_quarter:
                winners_by_quarter[quarter] = []
            winners_by_quarter[quarter].append(winner['participant_id'])

        context['winners_by_quarter'] = winners_by_quarter
        context['form'] = form
        context['venmo_link'] = "https://venmo.com/u/A1ecWilliams"
        context['remaining_squares'] = remaining_squares
        context['initial_cap'] = initial_cap

    else:
        context['participant_name'] = None

    print("Participant ID from cookie:", participant_id)
    print("Participant exists:", participant is not None)
    
    return render(request, 'Squares/home.html', context)


def grid(request):
    participant_id = request.COOKIES.get('participant_id', None)
    squares = Square.objects.all().order_by('row', 'column')
    grid_layout = [[None for _ in range(10)] for _ in range(10)]

    try:
        latest_game_score = GameScore.objects.latest('id')
    except GameScore.DoesNotExist:
        latest_game_score = None

    for square in squares:
        row = square.row
        column = square.column

        if latest_game_score:
            kc_last_digit = latest_game_score.kc_score % 10
            sf_last_digit = latest_game_score.sf_score % 10
            square.is_current_winner = (row == sf_last_digit and column == kc_last_digit)
        else:
            square.is_current_winner = False

        square.is_finalized_winner = WinningQuarter.objects.filter(square = square, game_score__quarter_finalized__isnull=False).exists()
    
        grid_layout[row][column] = square

    context = {
        'grid': list(enumerate(grid_layout)),
        'current_participant_id': participant_id,
        'kc_score': latest_game_score.kc_score if latest_game_score else None,
        'sf_score': latest_game_score.sf_score if latest_game_score else None,
        'finalized_quarter': latest_game_score.quarter_finalized if latest_game_score else '',
    }

    return render(request, 'Squares/grid.html', context)