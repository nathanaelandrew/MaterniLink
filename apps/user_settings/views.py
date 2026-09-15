from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import UserSettings


@login_required
def settings_view(request):
    settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        settings_obj.dark_mode = 'dark_mode' in request.POST
        settings_obj.email_notifications = 'email_notifications' in request.POST
        settings_obj.save()
        messages.success(request, 'Settings saved.')
        return redirect('user_settings:settings')

    return render(request, 'user_settings/settings.html', {'settings_obj': settings_obj})