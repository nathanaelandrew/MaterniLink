# apps/user_settings/urls.py
from django.urls import path
from .views import settings_view

app_name = 'user_settings'

urlpatterns = [
    path('', settings_view, name='settings'),
]