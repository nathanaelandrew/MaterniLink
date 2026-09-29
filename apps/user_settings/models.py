from django.db import models
from django.conf import settings

class UserSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='settings'
    )
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)