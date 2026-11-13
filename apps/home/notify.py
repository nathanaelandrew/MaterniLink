"""One place to create in-app notifications."""
from apps.profile.models import Notification


def notify(user, title, content, link=''):
    """Create a notification for `user`. Never raises: a failed notification
    must not break the action that triggered it."""
    if user is None:
        return
    try:
        Notification.objects.create(user=user, title=title[:255], content=content, link=link[:255])
    except Exception:
        pass