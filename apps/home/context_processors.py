from apps.profile.models import Message, Notification


def badges(request):
    """Unread counts for the header icons."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    return {
        'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
        'unread_messages': Message.objects.filter(receiver=user, is_read=False).count(),
    }