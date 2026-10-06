from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.profile.models import MotherProfile, PregnancyProfile, MaternalHealthLog, Appointment
from datetime import date

@login_required
def dashboard(request):
    user = request.user
    
    # 1. Fetch Mother Profile from the profile app
    mother = MotherProfile.objects.filter(user=user).first()
    
    # 2. Fetch Active Pregnancy & Calculate Weeks
    pregnancy = PregnancyProfile.objects.filter(mother=mother, pregnancy_status='Ongoing').first()
    weeks = 0
    doctor_name = "Dr. Mendoza" # Default fallback
    
    if pregnancy:
        if pregnancy.lmp_date:
            delta = date.today() - pregnancy.lmp_date
            weeks = max(0, delta.days // 7)
        
        if pregnancy.doctor:
            doctor_name = f"Dr. {pregnancy.doctor.last_name}"
            
    # 3. Get latest vitals for the metrics card
    latest_log = MaternalHealthLog.objects.filter(pregnancy=pregnancy).order_by('-log_date').first()
    
    # 4. Get upcoming appointments for the bottom section
    appointments = Appointment.objects.filter(mother=mother).order_by('scheduled_datetime')[:3]

    return render(request, 'home/mother_dashboard.html', {
        'mother': mother,
        'weeks': weeks,
        'latest_log': latest_log,
        'doctor_name': doctor_name,
        'appointments': appointments
    })