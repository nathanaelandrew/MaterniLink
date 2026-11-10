from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MotherProfile, DoctorProfile, PregnancyProfile
from .forms import MaternalHealthLogForm, AppointmentRequestForm
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

@login_required
def appointments_view(request):
    user = request.user
    mother = MotherProfile.objects.filter(user=user).first()

    if not mother:
        messages.error(request, "Mother profile not found. Please log in as a Mother.")
        return redirect('home:dashboard')

    # Seed a default doctor if none exists in database so dropdown works
    if not DoctorProfile.objects.exists():
        DoctorProfile.objects.create(
            user=user,
            first_name="Maria",
            last_name="Mendoza",
            license_number="MD-10924",
            specialization="Obstetrics & Gynecology",
            phone_number="0917-123-4567",
            clinic_address="Room 304, Medical Arts Bldg."
        )

    active_pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()
    default_doctor = active_pregnancy.doctor if active_pregnancy else DoctorProfile.objects.first()

    if request.method == 'POST':
        form = AppointmentRequestForm(request.POST)
        if form.is_valid():
            Appointment.objects.create(
                mother=mother,
                doctor=form.cleaned_data['doctor'],
                scheduled_datetime=form.cleaned_data['scheduled_datetime'],
                reason=form.cleaned_data['reason'],
                status='Pending'
            )
            messages.success(request, "Appointment request sent successfully!")
            return redirect('profile:appointments')
    else:
        form = AppointmentRequestForm(initial={'doctor': default_doctor})

    # Fetch all appointments for this mother (latest first)
    my_appointments = Appointment.objects.filter(mother=mother).order_by('-scheduled_datetime')

    return render(request, 'profile/appointments.html', {
        'form': form,
        'appointments': my_appointments,
        'mother': mother,
    })