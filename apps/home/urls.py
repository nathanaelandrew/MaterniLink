from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kick-counter/', views.kick_counter, name='kick_counter'),
]