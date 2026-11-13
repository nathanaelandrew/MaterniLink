from apps.profile.models import Message, Notification
from apps.user_settings.models import UserSettings


def badges(request):
    """Unread counts for the header icons, and the user's display preferences."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    return {
        'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
        'unread_messages': Message.objects.filter(receiver=user, is_read=False).count(),
        # An unsaved default object when the user has never opened Settings.
        'prefs': UserSettings.objects.filter(user=user).first() or UserSettings(user=user),
    }