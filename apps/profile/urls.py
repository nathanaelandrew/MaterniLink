from . import views
from django.urls import path
from .views import profile_view

app_name = 'profile'
urlpatterns = [
    path('', profile_view, name='profile'),
    path('log-vitals/', views.add_health_log, name='add_health_log'),
    ]