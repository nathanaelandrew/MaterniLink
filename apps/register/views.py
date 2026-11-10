from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm
from apps.profile.models import MotherProfile, DoctorProfile
import uuid

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home:dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            role = form.cleaned_data.get('role')
            user.role = role
            user.status = 'Active'
            user.save()

            if role == 'Mother':
                MotherProfile.objects.create(
                    user=user,
                    first_name=user.username,
                    last_name='',
                    date_of_birth='2000-01-01',
                    blood_type='O+',
                    emergency_contact_name='Emergency Contact',
                    emergency_contact_phone='000-000-0000'
                )
            elif role == 'Doctor':
                # Generate a temporary unique license number
                temp_license = f"MD-{uuid.uuid4().hex[:6].upper()}"
                DoctorProfile.objects.create(
                    user=user,
                    first_name=user.username,
                    last_name='Doctor',
                    license_number=temp_license,
                    specialization='Obstetrics & Gynecology',
                    phone_number='000-000-0000',
                    clinic_address='Main Hospital'
                )

            login(request, user)
            return redirect('home:dashboard')
    else:
        form = SignUpForm()

    return render(request, 'register/register.html', {'form': form})