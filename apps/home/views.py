from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
from django.utils import timezone
from .doctor_views import doctor_dashboard
from .mother_views import annotate_reminders

from apps.profile.models import (
    MotherProfile,
    PregnancyProfile,
    MaternalHealthLog,
    Appointment,
    KickCountLog,
    MedicalOrderRequest,
    Reminder
)

@login_required
def dashboard(request):
    user = request.user
    
    # Doctors get their own dashboard
    if user.role == 'Doctor':
        return doctor_dashboard(request)
    
    # 1. Fetch Mother Profile
    mother = MotherProfile.objects.filter(user=user).first()
    
    # 2. Fetch Active Pregnancy & Calculate Weeks
    pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()
    weeks = 0
    doctor_name = "Dr. Mendoza"
    
    if pregnancy:
        if pregnancy.lmp_date:
            delta = date.today() - pregnancy.lmp_date
            weeks = max(0, delta.days // 7)
        
        if pregnancy.doctor:
            doctor_name = f"Dr. {pregnancy.doctor.last_name}"
            
    # 3. Get latest vitals
    latest_log = MaternalHealthLog.objects.filter(pregnancy=pregnancy).order_by('-log_date').first()
    
    # 4. Get upcoming appointments
    appointments = Appointment.objects.filter(mother=mother).order_by('scheduled_datetime')[:3]

    # 5. Today's reminders (first five; the full list lives on /home/reminders/)
    all_reminders = annotate_reminders(
        Reminder.objects.filter(mother=mother, is_active=True).order_by('scheduled_time', 'reminder_id')
    ) if mother else []

    open_requests = MedicalOrderRequest.objects.filter(
        pregnancy__mother=mother, status='Requested').count() if mother else 0

    return render(request, 'home/mother_dashboard.html', {
        'reminders': all_reminders[:5],
        'reminders_total': len(all_reminders),
        'reminders_left': sum(1 for r in all_reminders if not r.done),
        'mother': mother,
        'weeks': weeks,
        'latest_log': latest_log,
        'doctor_name': doctor_name,
        'appointments': appointments
    })


@login_required
def kick_counter(request):
    user = request.user
    mother = MotherProfile.objects.filter(user=user).first()

    if not mother:
        messages.error(request, "Mother profile not found.")
        return redirect('home:dashboard')

    pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()
    if not pregnancy:
        pregnancy = PregnancyProfile.objects.create(
            mother=mother,
            lmp_date=timezone.now().date() - timedelta(weeks=20),
            edd_date=timezone.now().date() + timedelta(weeks=20),
            pregnancy_status='Ongoing'
        )

    if request.method == 'POST':
        kick_count = int(request.POST.get('kick_count', 0))
        duration_minutes = max(1, int(request.POST.get('duration_minutes', 1)))

        end_time = timezone.now()
        start_time = end_time - timedelta(minutes=duration_minutes)

        KickCountLog.objects.create(
            pregnancy=pregnancy,
            start_time=start_time,
            end_time=end_time,
            kick_count=kick_count,
            duration_minutes=duration_minutes
        )
        messages.success(request, f"Kick session saved! Recorded {kick_count} movements in {duration_minutes} min.")
        return redirect('home:kick_counter')

    past_sessions = KickCountLog.objects.filter(pregnancy=pregnancy).order_by('-start_time')[:8]

    return render(request, 'home/kick_counter.html', {
        'mother': mother,
        'pregnancy': pregnancy,
        'past_sessions': past_sessions,
    })