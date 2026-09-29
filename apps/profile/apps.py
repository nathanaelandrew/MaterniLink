# maternilink/apps/profile/apps.py
from django.apps import AppConfig

class ProfileConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.profile'  # The full path
    label = 'profile'       # The short name used in AUTH_USER_MODEL