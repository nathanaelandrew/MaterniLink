from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, datetime
from django.utils import timezone

# 1. All necessary models from the ERD
from .models import (
    MotherProfile,
    DoctorProfile,
    PregnancyProfile,
    Appointment,
    MaternalHealthLog
)

# 2. All necessary forms
from .forms import MaternalHealthLogForm, AppointmentRequestForm


@login_required
def profile_view(request):
    user = request.user

    if user.role == 'Doctor':
        profile = get_object_or_404(DoctorProfile, user=user)
        # (field, label, input type, required)
        fields = [
            ('first_name', 'First name', 'text', True),
            ('last_name', 'Last name', 'text', True),
            ('specialization', 'Specialization', 'text', True),
            ('phone_number', 'Phone number', 'tel', True),
            ('clinic_address', 'Clinic address', 'textarea', True),
        ]
        readonly = [('License number', profile.license_number)]
    else:
        profile, _ = MotherProfile.objects.get_or_create(
            user=user,
            defaults={
                'first_name': user.username,
                'last_name': 'User',
                'date_of_birth': '2000-01-01',
                'blood_type': 'O+',
                'emergency_contact_name': 'Emergency Contact',
                'emergency_contact_phone': '000-000-0000',
            }
        )
        fields = [
            ('first_name', 'First name', 'text', True),
            ('last_name', 'Last name', 'text', True),
            ('date_of_birth', 'Date of birth', 'date', True),
            ('blood_type', 'Blood type', 'text', True),
            ('emergency_contact_name', 'Emergency contact name', 'text', True),
            ('emergency_contact_phone', 'Emergency contact phone', 'tel', True),
        ]
        readonly = []

    errors = {}
    if request.method == 'POST':
        values = {n: request.POST.get(n, '').strip() for n, *_ in fields}
        for name, label, kind, required in fields:
            if required and not values[name]:
                errors[name] = f"{label} is required."
        if 'date_of_birth' in values and 'date_of_birth' not in errors:
            try:
                dob = datetime.strptime(values['date_of_birth'], '%Y-%m-%d').date()
                if dob >= timezone.localdate():
                    errors['date_of_birth'] = "Date of birth must be in the past."
            except ValueError:
                errors['date_of_birth'] = "Enter a valid date."
        if not errors:
            for name, val in values.items():
                setattr(profile, name, val)
            profile.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile:profile')
    else:
        values = {n: getattr(profile, n) for n, *_ in fields}

    rows = [{
        'name': n, 'label': l, 'kind': k,
        'value': values[n].isoformat() if hasattr(values[n], 'isoformat') else values[n],
        'error': errors.get(n),
    } for n, l, k, _ in fields]

    return render(request, 'profile/profile.html', {
        'profile': profile, 'rows': rows, 'readonly': readonly,
        'is_doctor': user.role == 'Doctor',
    })

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
            messages.success(request, "Your appointment request has been sent for review.")
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