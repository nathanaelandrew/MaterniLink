from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import Profile

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        profile.full_name = request.POST.get('full_name', '').strip()
        profile.bio = request.POST.get('bio', '').strip()
        profile.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile:profile')
    return render(request, 'profile/profile.html', {'profile': profile})