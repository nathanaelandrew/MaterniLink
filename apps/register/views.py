from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm 
from apps.profile.models import MotherProfile, DoctorProfile

def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            role = form.cleaned_data.get('role')
            user.role = role
            user.save()
            
            if role == 'Mother':
                MotherProfile.objects.create(
                    user=user, 
                    date_of_birth="2000-01-01"
                )
            elif role == 'Doctor':
                DoctorProfile.objects.create(user=user)
                
            login(request, user)
            return redirect('home:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'register/register.html', {'form': form})