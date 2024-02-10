from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.models import Group, User
from .models import Participant, Square, GameScore, WinningQuarter
from .forms import ScoreUpdateForm, RevertSquaresForm
import random
from .global_vars import cap_enabled

admin.site.unregister(User)
admin.site.unregister(Group)


class WinningQuarterInline(admin.TabularInline):
    model = WinningQuarter
    extra = 0


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['name', 'squares_pending', 'squares_purchased', 'purchase_complete']

    @admin.action(description='Approve Selected Purchase(s)')
    def approve_purchases(self, request, queryset):
        for participant in queryset:
            participant.squares_purchased += participant.squares_pending
            participant.squares_pending = 0
            participant.purchase_complete = True
            participant.save()

    @admin.action(description='Randomly Assign Squares')
    def randomly_assign_squares(modeladmin, request, queryset):

        inverse_probability_distribution = {
        0.05691464255929723: {(2, 2), (5, 5)},
        0.029682756167288986: {(5, 9), (9, 5)},
        0.020076686210237536: {(5, 2), (2, 5), (9, 8), (8, 9)},
        0.015167960975460632: {(5, 1), (1, 5), (9, 1), (1, 9), (3, 2), (2, 3), (5, 4), (4, 5), (8, 5), (5, 8), (8, 8), (9, 9)},
        0.012188007935095085: {(2, 1), (1, 2), (4, 2), (2, 4), (6, 2), (2, 6), (9, 2), (2, 9), (7, 5), (5, 7)},
        0.01018669300322397: {(8, 2), (2, 8), (5, 3), (3, 5), (9, 4), (4, 9), (9, 6), (6, 9), (8, 6), (6, 8)},
        0.008749923891344708: {(1, 1), (6, 1), (1, 6), (8, 3), (3, 8), (4, 4), (6, 5), (5, 6)},
        0.0076683510988422715: {(8, 0), (0, 8), (7, 2), (2, 7), (9, 3), (3, 9), (8, 7), (7, 8)},
        0.006824748117671506: {(9, 0), (0, 9), (8, 4), (4, 8)},
        0.006148360791836867: {(6, 6), (7, 6), (6, 7), (9, 7), (7, 9)},
        0.005593954949471054: {(5, 0), (0, 5), (8, 1), (1, 8), (4, 3), (3, 4), (3, 3)},
        0.005131262232393215: {(3, 1), (1, 3), (6, 4), (4, 6)},
        0.004739263589735217: {(7, 1), (1, 7)},
        0.0036300152363741354: {(6, 3), (3, 6), (7, 7)},
        0.0032497098161149277: {(0, 0), (4, 1), (1, 4)},
        0.002941534394956566: {(6, 0), (0, 6)},
        0.002575216288486259: {(4, 0), (0, 4), (7, 3), (3, 7)},
        0.0022085069558431462: {(3, 0), (0, 3)},
        0.002061713539037354: {(7, 4), (4, 7)},
        0.0018747948138299782: {(7, 0), (0, 7)},
    }
        squares_list = [(square, prob) for prob, squares in inverse_probability_distribution.items() for square in squares]
        all_unassigned_squares = list(Square.objects.filter(owner__isnull=True))
        square_tuples = [(square.row, square.column) for square in all_unassigned_squares]

        filtered_squares_list = [square for square in squares_list if square[0] in square_tuples]
        squares, probabilities = zip(*[(square, prob) for square, prob in filtered_squares_list])

        participants = Participant.objects.annotate(assigned_squares_count=Count('square')).filter(squares_purchased__gt=F('assigned_squares_count'))
        for participant in participants:
            needed_squares = participant.squares_purchased - participant.assigned_squares_count
            for _ in range(min(needed_squares, len(squares))):
                chosen_square = random.choices(squares, weights=probabilities, k=1)[0]
                square_obj = next((s for s in all_unassigned_squares if (s.row, s.column) == chosen_square), None)
                if square_obj:
                    square_obj.owner = participant
                    square_obj.save()
                    index = squares.index(chosen_square)
                    squares = squares[:index] + squares[index + 1:]
                    probabilities = probabilities[:index] + probabilities[index + 1:]
        
        cap_enabled = False
        
        messages.success(request, 'Squares assigned!')

    @admin.action(description='Revert Selected Squares')
    def revert_squares(self, request, queryset):
        selected = request.POST.getlist('_selected_action')
        request.session['participant_ids_for_reversion'] = selected
        return redirect('admin:revert_squares')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Make sure to name your URL pattern
            path('revert-squares/', self.admin_site.admin_view(self.revert_squares_view), name='revert_squares'),
        ]
        # Add your custom URLs at the beginning of the list so they have priority
        return custom_urls + urls
    
    def revert_squares_view(self, request):
        if 'apply' in request.POST:
            form = RevertSquaresForm(request.POST)
            if form.is_valid():
                num_squares_to_revert = form.cleaned_data['num_squares_to_revert']
                square_type = form.cleaned_data['square_type']
                participant_ids = request.session.get('participant_ids_for_reversion', [])
                for participant_id in participant_ids:
                    participant = Participant.objects.get(id=participant_id)
                    if square_type == 'purchased':
                        participant.revert_purchased_squares(num_squares_to_revert)
                    elif square_type == 'pending':
                        participant.revert_pending_squares(num_squares_to_revert)
                    participant.purchase_complete = False
                    participant.save()
                return redirect('../')
        
        else:
            if 'action_checkbox' in request.POST:
                request.session['participant_ids_for_reversion'] = request.POST.getlist('_selected_action')
            form = RevertSquaresForm()

        return render(request,'admin/revert_squares_form.html', {'form': form})
    
@admin.register(Square)
class SquareAdmin(admin.ModelAdmin):
    list_display = ['row', 'column', 'owner']
    inlines = [WinningQuarterInline]
    search_fields = ['row', 'column', 'owner__name']
    list_filter = ['owner']
    

@admin.register(GameScore)
class GameScoreAdmin(admin.ModelAdmin):
    list_display = ['kc_score','sf_score', 'quarter_finalized']
    #inlines = [WinningQuarterInline]
    change_list_template = 'admin/score_change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('update_scores/', self.admin_site.admin_view(self.update_scores_view), name='update_scores'),
        ]
        return custom_urls + urls
    
    def update_scores_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title = 'Update Game Score'
        )

        if request.method == 'POST':
            print("Processing POST request in update_scores_view")
            form = ScoreUpdateForm(request.POST)
            if form.is_valid():
                game_score = form.save(commit=False)
                game_score.save()
                self.handle_winning_squares(game_score, request)
                messages.success(request, 'Scores updated successfully.')
                return HttpResponseRedirect('../')
        else:
            form = ScoreUpdateForm()
        context['form'] = form
        return render(request, 'admin/update_scores.html', context)
    
    def handle_winning_squares(self, game_score, request):
        if game_score.quarter_finalized:
            kc_last_digit = game_score.kc_score % 10
            sf_last_digit = game_score.sf_score % 10

            winning_square = Square.objects.get(row=sf_last_digit, column=kc_last_digit)
            WinningQuarter.objects.get_or_create(game_score=game_score, square=winning_square)
            print("handle_winning_squares called for GameScore ID:", game_score.id)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.quarter_finalized:
            self.handle_winning_squares(obj, request)