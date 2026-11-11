"""Doctor-side views: dashboard, appointment requests, patient index, calendar."""
import calendar as pycal
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.profile.models import (
    Appointment,
    DoctorProfile,
    KickCountLog,
    MaternalHealthLog,
    MotherProfile,
    PregnancyProfile,
)

# Statuses that mean "this visit has a time on the doctor's calendar".
CONFIRMED = ('Accepted', 'Confirmed', 'Rescheduled')

# Visits closer together than this are treated as a clash.
SLOT = timedelta(minutes=30)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def doctor_required(view):
    """Only logged-in doctors get in. The view receives the DoctorProfile."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'Doctor':
            return redirect('home:dashboard')

        # A doctor account should always have a profile (registration creates
        # one). If it's missing, create a placeholder instead of looping
        # between "/" and the dashboard.
        doctor, _ = DoctorProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'first_name': request.user.username,
                'last_name': 'Doctor',
                'license_number': f"MD-{uuid.uuid4().hex[:6].upper()}",
                'specialization': 'Obstetrics & Gynecology',
                'phone_number': '000-000-0000',
                'clinic_address': 'Main Hospital',
            },
        )
        return view(request, doctor, *args, **kwargs)
    return wrapper


def patients_of(doctor):
    """Mothers linked to this doctor by a pregnancy or by any appointment."""
    return MotherProfile.objects.filter(
        Q(pregnancyprofile__doctor=doctor) | Q(appointment__doctor=doctor)
    ).distinct()


def weeks_for(pregnancy):
    if pregnancy and pregnancy.lmp_date:
        return max(0, (date.today() - pregnancy.lmp_date).days // 7)
    return 0


def trimester_for(weeks):
    return 1 if weeks < 14 else 2 if weeks < 28 else 3


def age_of(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def has_clash(doctor, when, exclude_pk=None):
    clash = Appointment.objects.filter(
        doctor=doctor,
        status__in=CONFIRMED,
        scheduled_datetime__gt=when - SLOT,
        scheduled_datetime__lt=when + SLOT,
    )
    if exclude_pk:
        clash = clash.exclude(pk=exclude_pk)
    return clash.exists()


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@doctor_required
def doctor_dashboard(request, doctor):
    now = timezone.now()
    today = timezone.localdate()
    appts = Appointment.objects.filter(doctor=doctor).select_related('mother')

    todays = appts.filter(
        scheduled_datetime__date=today, status__in=CONFIRMED
    ).order_by('scheduled_datetime')
    pending_qs = appts.filter(status='Pending')
    upcoming = appts.filter(
        scheduled_datetime__gte=now, status__in=CONFIRMED
    ).order_by('scheduled_datetime')[:4]

    return render(request, 'home/doctor_dashboard.html', {
        'doctor': doctor,
        'patient_count': patients_of(doctor).count(),
        'pending_count': pending_qs.count(),
        'today_count': todays.count(),
        'todays': todays,
        'pending_preview': pending_qs.order_by('scheduled_datetime')[:4],
        'upcoming': upcoming,
    })


# --------------------------------------------------------------------------
# Appointment requests
# --------------------------------------------------------------------------
@doctor_required
def doctor_requests(request, doctor):
    now = timezone.now()
    base = Appointment.objects.filter(doctor=doctor).select_related('mother')

    pending = base.filter(status='Pending').order_by('scheduled_datetime')
    upcoming = base.filter(
        status__in=CONFIRMED, scheduled_datetime__gte=now
    ).order_by('scheduled_datetime')
    history = base.filter(
        Q(status='Declined') | Q(scheduled_datetime__lt=now)
    ).exclude(status='Pending').order_by('-scheduled_datetime')

    tab = request.GET.get('tab', 'pending')
    tabs = {'pending': pending, 'upcoming': upcoming, 'history': history}
    if tab not in tabs:
        tab = 'pending'

    return render(request, 'home/doctor_requests.html', {
        'doctor': doctor,
        'tab': tab,
        'appointments': tabs[tab],
        'counts': {k: v.count() for k, v in tabs.items()},
        'today': timezone.localdate().isoformat(),
    })


@doctor_required
@require_POST
def appointment_respond(request, doctor, appointment_id):
    """Accept, decline or reschedule one of this doctor's appointments."""
    appt = get_object_or_404(Appointment, pk=appointment_id, doctor=doctor)
    action = request.POST.get('action')
    patient = f"{appt.mother.first_name} {appt.mother.last_name}".strip()

    if action == 'accept':
        if has_clash(doctor, appt.scheduled_datetime, exclude_pk=appt.pk):
            messages.error(request, "You already have a visit within 30 minutes of that time. Reschedule instead.")
        else:
            appt.status = 'Accepted'
            appt.save(update_fields=['status'])
            messages.success(request, f"Appointment with {patient} accepted.")

    elif action == 'decline':
        appt.status = 'Declined'
        appt.save(update_fields=['status'])
        messages.success(request, f"Appointment with {patient} declined.")

    elif action == 'reschedule':
        try:
            naive = datetime.strptime(
                f"{request.POST.get('date', '')} {request.POST.get('time', '')[:5]}",
                '%Y-%m-%d %H:%M',
            )
            new_dt = timezone.make_aware(naive)
        except ValueError:
            messages.error(request, "Please choose a valid date and time.")
        else:
            if new_dt < timezone.now():
                messages.error(request, "The new time must be in the future.")
            elif has_clash(doctor, new_dt, exclude_pk=appt.pk):
                messages.error(request, "You already have a visit within 30 minutes of that time.")
            else:
                appt.scheduled_datetime = new_dt
                appt.status = 'Rescheduled'
                appt.save(update_fields=['scheduled_datetime', 'status'])
                messages.success(request, f"Appointment with {patient} moved to {new_dt.strftime('%b %d at %I:%M %p')}.")
    else:
        messages.error(request, "Unknown action.")

    # Go back to where the doctor came from (whitelisted, never a raw URL).
    if request.POST.get('return_to') == 'dashboard':
        return redirect('home:dashboard')
    tab = request.POST.get('tab')
    if tab not in ('pending', 'upcoming', 'history'):
        tab = 'pending'
    return redirect(f"{reverse('home:doctor_requests')}?tab={tab}")


# --------------------------------------------------------------------------
# Patient index and patient chart
# --------------------------------------------------------------------------
@doctor_required
def doctor_patients(request, doctor):
    q = request.GET.get('q', '').strip()
    patients = patients_of(doctor)
    if q:
        patients = patients.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    patients = list(patients.order_by('last_name', 'first_name'))

    pregnancies = {}
    for p in PregnancyProfile.objects.filter(
        mother__in=patients, pregnancy_status='Ongoing'
    ).order_by('created_at'):
        pregnancies[p.mother_id] = p  # latest one wins

    next_visit = {}
    for a in Appointment.objects.filter(
        doctor=doctor, mother__in=patients,
        status__in=CONFIRMED, scheduled_datetime__gte=timezone.now(),
    ).order_by('-scheduled_datetime'):
        next_visit[a.mother_id] = a.scheduled_datetime  # earliest ends up last

    rows = []
    for m in patients:
        preg = pregnancies.get(m.pk)
        weeks = weeks_for(preg)
        rows.append({
            'mother': m,
            'age': age_of(m.date_of_birth),
            'pregnancy': preg,
            'weeks': weeks,
            'trimester': trimester_for(weeks) if preg else None,
            'next_visit': next_visit.get(m.pk),
        })

    return render(request, 'home/doctor_patients.html', {
        'doctor': doctor,
        'rows': rows,
        'q': q,
    })


@doctor_required
def doctor_patient_detail(request, doctor, mother_id):
    # Only patients linked to this doctor can be opened.
    mother = get_object_or_404(patients_of(doctor), pk=mother_id)

    pregnancy = PregnancyProfile.objects.filter(
        mother=mother, pregnancy_status='Ongoing'
    ).order_by('-created_at').first()
    weeks = weeks_for(pregnancy)

    logs = MaternalHealthLog.objects.filter(pregnancy=pregnancy).order_by('-log_date')[:8] if pregnancy else []
    kicks = KickCountLog.objects.filter(pregnancy=pregnancy).order_by('-start_time')[:5] if pregnancy else []
    visits = Appointment.objects.filter(mother=mother, doctor=doctor).order_by('-scheduled_datetime')[:10]

    return render(request, 'home/doctor_patient_detail.html', {
        'doctor': doctor,
        # Not called "mother": base.html uses that name for the logged-in user.
        'patient': mother,
        'age': age_of(mother.date_of_birth),
        'pregnancy': pregnancy,
        'weeks': weeks,
        'trimester': trimester_for(weeks),
        'latest_log': logs[0] if logs else None,
        'logs': logs,
        'kicks': kicks,
        'visits': visits,
    })


# --------------------------------------------------------------------------
# Calendar
# --------------------------------------------------------------------------
@doctor_required
def doctor_calendar(request, doctor):
    today = timezone.localdate()
    try:
        year, month = (int(x) for x in request.GET.get('month', '').split('-'))
        first = date(year, month, 1)
        if not 2000 <= year <= 2100:
            raise ValueError
    except ValueError:
        first = today.replace(day=1)

    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = (first + timedelta(days=32)).replace(day=1)

    weeks = pycal.Calendar(firstweekday=6).monthdatescalendar(first.year, first.month)
    start = timezone.make_aware(datetime.combine(weeks[0][0], time.min))
    end = timezone.make_aware(datetime.combine(weeks[-1][-1] + timedelta(days=1), time.min))

    by_day = defaultdict(list)
    for a in Appointment.objects.filter(
        doctor=doctor, status__in=CONFIRMED,
        scheduled_datetime__gte=start, scheduled_datetime__lt=end,
    ).select_related('mother').order_by('scheduled_datetime'):
        by_day[timezone.localtime(a.scheduled_datetime).date()].append(a)

    grid = [[{
        'date': d,
        'in_month': d.month == first.month,
        'is_today': d == today,
        'appts': by_day.get(d, []),
    } for d in week] for week in weeks]

    agenda = [{'date': d, 'appts': items}
              for d, items in sorted(by_day.items()) if d.month == first.month]

    return render(request, 'home/doctor_calendar.html', {
        'doctor': doctor,
        'month_label': first.strftime('%B %Y'),
        'prev_month': prev_month.strftime('%Y-%m'),
        'next_month': next_month.strftime('%Y-%m'),
        'is_current': first == today.replace(day=1),
        'grid': grid,
        'agenda': agenda,
        'weekdays': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    })