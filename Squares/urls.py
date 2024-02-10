from django.urls import path
from .views import register_participant, home, grid, dickroll


urlpatterns = [
    path('register/', register_participant, name='register'),
    path('', home, name='home'),
    path('grid/', grid, name='grid'),
    path('dickroll/', dickroll, name='dickroll'),
]