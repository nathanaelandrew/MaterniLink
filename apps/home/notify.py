"""One place to create in-app notifications (and their optional email)."""
from django.conf import settings
from django.core.mail import send_mail

from apps.profile.models import Notification
from apps.user_settings.models import UserSettings


def notify(user, title, content, link=''):
    """Create a notification for `user`. Never raises: a failed notification
    must not break the action that triggered it."""
    if user is None:
        return
    try:
        Notification.objects.create(user=user, title=title[:255], content=content, link=link[:255])
    except Exception:
        return

    # Email copy, if the user wants it. The email only says that something is
    # waiting: health details stay inside the app.
    try:
        prefs = UserSettings.objects.filter(user=user).first()
        wants_email = prefs.email_notifications if prefs else True
        if wants_email and user.email:
            send_mail(
                subject=f"MaterniLink: {title}",
                message=("You have a new notification in MaterniLink.\n\n"
                         f"{title}\n\nLog in to see the details."),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[user.email],
                fail_silently=True,
            )
    except Exception:
        pass