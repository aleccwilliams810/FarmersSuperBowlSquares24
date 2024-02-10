from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.models import Group, User
from .models import Participant, Square, GameScore, WinningQuarter
from .forms import ScoreUpdateForm, RevertSquaresForm
import random

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
        all_unassigned_squares = list(Square.objects.filter(owner__isnull=True))
        random.shuffle(all_unassigned_squares)

        participants = Participant.objects.annotate(assigned_squares_count=Count('square')).filter(squares_purchased__gt=F('assigned_squares_count'))
        for participant in participants:
            needed_squares = participant.squares_purchased - participant.assigned_squares_count
            for _ in range(min(needed_squares, len(all_unassigned_squares))):
                if all_unassigned_squares:
                    square = all_unassigned_squares.pop()
                    square.owner = participant
                    square.save()
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