from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MotherProfile, DoctorProfile, PregnancyProfile
from .forms import MaternalHealthLogForm
from datetime import date

@login_required
def profile_view(request):
    user = request.user
    
    # Fetch the appropriate profile based on role
    if user.role == 'Doctor':
        profile = get_object_or_404(DoctorProfile, user=user)
        template = 'profile/doctor_profile.html'
    else:
        # Default to Mother profile
        profile, created = MotherProfile.objects.get_or_create(
            user=user, 
            defaults={'first_name': user.username, 'last_name': 'User', 'date_of_birth': '2000-01-01'}
        )
        template = 'profile/mother_profile.html'

    if request.method == 'POST':
        profile.first_name = request.POST.get('first_name', '').strip()
        profile.last_name = request.POST.get('last_name', '').strip()
        profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile:profile')

    return render(request, template, {'profile': profile})

@login_required
def add_health_log(request):
    mother = MotherProfile.objects.filter(user=request.user).first()
    pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()

    if not pregnancy:
        messages.error(request, "You need an active pregnancy profile to log vitals.")
        return redirect('home:dashboard')

    if request.method == 'POST':
        form = MaternalHealthLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.pregnancy = pregnancy
            log.save()
            messages.success(request, "Vitals recorded successfully.")
            return redirect('home:dashboard')
    else:
        form = MaternalHealthLogForm(initial={'log_date': date.today()})

    return render(request, 'profile/health_log_form.html', {'form': form})