from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST
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
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import MaternalHealthLogForm, AppointmentRequestForm, StartPregnancyForm
from .utils import calculate_edd


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
        messages.info(request, "Set up your pregnancy first, then you can log your vitals.")
        return redirect(f"{reverse('profile:start_pregnancy')}?next={reverse('profile:add_health_log')}")

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

    # Only real doctor accounts can be booked.
    doctors = DoctorProfile.objects.filter(user__role='Doctor')

    active_pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()
    default_doctor = active_pregnancy.doctor if active_pregnancy and active_pregnancy.doctor else doctors.first()

    if request.method == 'POST':
        form = AppointmentRequestForm(request.POST, mother=mother)
        if form.is_valid():
            Appointment.objects.create(
                mother=mother,
                doctor=form.cleaned_data['doctor'],
                scheduled_datetime=form.cleaned_data['scheduled_datetime'],
                reason=form.cleaned_data['reason'],
                status='Pending'
            )
            messages.success(request, "Your appointment request has been sent for review.")
            chosen = form.cleaned_data['doctor']
            if chosen.user_id != user.pk:
                from apps.home.notify import notify
                notify(chosen.user, "New appointment request",
                       f"{mother.first_name} {mother.last_name} requested a visit on "
                       f"{form.cleaned_data['scheduled_datetime'].strftime('%b %d at %I:%M %p')}.",
                       '/home/requests/')
            return redirect('profile:appointments')
    else:
        form = AppointmentRequestForm(initial={'doctor': default_doctor})

    my_appointments = Appointment.objects.filter(mother=mother).order_by('-scheduled_datetime')

    return render(request, 'profile/appointments.html', {
        'form': form,
        'appointments': my_appointments,
        'mother': mother,
        'has_doctors': doctors.exists(),
    })

@login_required
@require_POST
def cancel_appointment(request, appointment_id):
    """Let a mother withdraw her own request while it is still pending."""
    mother = MotherProfile.objects.filter(user=request.user).first()
    if not mother:
        return redirect('home:dashboard')

    appt = get_object_or_404(Appointment, pk=appointment_id, mother=mother)
    if appt.status != 'Pending':
        messages.error(request, "Only pending requests can be cancelled. Message your doctor to change a confirmed visit.")
        return redirect('profile:appointments')

    appt.status = 'Cancelled'
    appt.save(update_fields=['status'])
    when = timezone.localtime(appt.scheduled_datetime).strftime('%b %d at %I:%M %p')
    messages.success(request, f"Your request for {when} was cancelled.")

    if appt.doctor.user_id != request.user.pk:
        from apps.home.notify import notify
        notify(appt.doctor.user, "Appointment request cancelled",
               f"{mother.first_name} {mother.last_name} cancelled her request for {when}.",
               f"{reverse('home:doctor_requests')}?tab=history")
    return redirect('profile:appointments')


@login_required
def start_pregnancy(request):
    """A mother sets her last period date; we create her pregnancy and due date."""
    if request.user.role != 'Mother':
        return redirect('home:dashboard')
    mother = MotherProfile.objects.filter(user=request.user).first()
    if not mother:
        return redirect('home:dashboard')

    # Only send her on to a page of this site.
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        next_url = ''

    if PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').exists():
        messages.info(request, "You're already tracking a pregnancy.")
        return redirect(next_url or 'home:dashboard')

    form = StartPregnancyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        lmp = form.cleaned_data['lmp_date']
        PregnancyProfile.objects.create(
            mother=mother, lmp_date=lmp, edd_date=calculate_edd(lmp), pregnancy_status='Ongoing')
        messages.success(request, f"All set! Your estimated due date is {calculate_edd(lmp):%B %d, %Y}.")
        return redirect(next_url or 'home:dashboard')

    return render(request, 'profile/start_pregnancy.html', {
        'form': form, 'mother': mother, 'next': next_url})