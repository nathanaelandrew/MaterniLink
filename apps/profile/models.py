from django.db import models
from django.contrib.auth.models import AbstractUser

# --- 1. Custom User Model (Matches 'USER' in ERD) ---
class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50)  # e.g., 'Doctor', 'Mother'
    status = models.CharField(max_length=50, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)

    # Resolve potential conflicts with Django's default permissions
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='maternilink_user_groups',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='maternilink_user_permissions',
        blank=True
    )

    def __str__(self):
        return self.username

# --- 2. Profile Entities ---
class DoctorProfile(models.Model):
    doctor_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100, unique=True)
    specialization = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    clinic_address = models.TextField()

    def __str__(self):
        return f"Dr. {self.last_name}"

class MotherProfile(models.Model):
    mother_id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mother_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    blood_type = models.CharField(max_length=5)
    emergency_contact_name = models.CharField(max_length=200)
    emergency_contact_phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# --- 3. Pregnancy Core ---
class PregnancyProfile(models.Model):
    pregnancy_id = models.BigAutoField(primary_key=True)
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.SET_NULL, null=True)
    lmp_date = models.DateField()
    edd_date = models.DateField()
    pregnancy_status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

# --- 4. Appointments & Notes ---
class Appointment(models.Model):
    appointment_id = models.BigAutoField(primary_key=True)
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    scheduled_datetime = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(max_length=50)

class ClinicalNote(models.Model):
    note_id = models.BigAutoField(primary_key=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    subjective_notes = models.TextField()
    objective_findings = models.TextField()
    assessment = models.TextField()
    clinical_plan = models.TextField()
    recorded_at = models.DateTimeField(auto_now_add=True)

# --- 5. Health Logs ---
class MaternalHealthLog(models.Model):
    maternal_log_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    log_date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    systolic_bp = models.IntegerField()
    diastolic_bp = models.IntegerField()
    notes = models.TextField(blank=True, null=True)

class KickCountLog(models.Model):
    kick_log_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    kick_count = models.IntegerField()
    duration_minutes = models.IntegerField()

class FetalHealthLog(models.Model):
    fetal_log_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    recorded_by_doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    fetal_heart_rate_bpm = models.IntegerField()
    fundal_height_cm = models.DecimalField(max_digits=5, decimal_places=2)
    gestational_age_weeks = models.IntegerField()
    recorded_date = models.DateField()

# --- 6. Medical Records & Orders ---
class MedicalOrderRequest(models.Model):
    request_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=100)
    test_name = models.CharField(max_length=200)
    status = models.CharField(max_length=50)
    instructions = models.TextField()

class Prescription(models.Model):
    prescription_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField()
    prescribed_date = models.DateField()

class MedicalRecord(models.Model):
    record_id = models.BigAutoField(primary_key=True)
    pregnancy = models.ForeignKey(PregnancyProfile, on_delete=models.CASCADE)
    request = models.ForeignKey(MedicalOrderRequest, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_by_user = models.ForeignKey(User, on_delete=models.CASCADE)
    file_url = models.URLField(max_length=500)
    record_type = models.CharField(max_length=100)
    summary_notes = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

# --- 7. Messaging & Reminders ---
class Notification(models.Model):
    notification_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    message_id = models.BigAutoField(primary_key=True)
    sender = models.ForeignKey(User, related_name='sent_msgs', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_msgs', on_delete=models.CASCADE)
    message_body = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

class Reminder(models.Model):
    reminder_id = models.BigAutoField(primary_key=True)
    mother = models.ForeignKey(MotherProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    reminder_type = models.CharField(max_length=100)
    scheduled_time = models.TimeField()
    frequency = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)