from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from .models import Appointment, DoctorProfile, MaternalHealthLog

# A visit takes a 30-minute slot.
SLOT = timedelta(minutes=30)
BOOKED = ('Accepted', 'Confirmed', 'Rescheduled')


class MaternalHealthLogForm(forms.ModelForm):
    class Meta:
        model = MaternalHealthLog
        fields = ['log_date', 'weight_kg', 'systolic_bp', 'diastolic_bp', 'notes']
        widgets = {
            'log_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.0'}),
            'systolic_bp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '120'}),
            'diastolic_bp': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '80'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'How are you feeling?'}),
        }
        error_messages = {
            'log_date': {'required': "Choose the date of this reading.", 'invalid': "Enter a valid date."},
            'weight_kg': {'required': "Enter your weight in kilograms.", 'invalid': "Enter your weight as a number, like 62.5."},
            'systolic_bp': {'required': "Enter the top number of your blood pressure.", 'invalid': "Enter a whole number, like 120."},
            'diastolic_bp': {'required': "Enter the bottom number of your blood pressure.", 'invalid': "Enter a whole number, like 80."},
        }

    def clean_log_date(self):
        d = self.cleaned_data['log_date']
        if d > timezone.localdate():
            raise forms.ValidationError("The date can't be in the future.")
        return d

    def clean_weight_kg(self):
        w = self.cleaned_data['weight_kg']
        if not 25 <= w <= 300:
            raise forms.ValidationError("Enter a weight between 25 and 300 kg.")
        return w

    def clean_systolic_bp(self):
        v = self.cleaned_data['systolic_bp']
        if not 50 <= v <= 260:
            raise forms.ValidationError("The top number should be between 50 and 260.")
        return v

    def clean_diastolic_bp(self):
        v = self.cleaned_data['diastolic_bp']
        if not 30 <= v <= 200:
            raise forms.ValidationError("The bottom number should be between 30 and 200.")
        return v

    def clean(self):
        cleaned = super().clean()
        top, bottom = cleaned.get('systolic_bp'), cleaned.get('diastolic_bp')
        if top is not None and bottom is not None and top <= bottom:
            self.add_error('systolic_bp', "The top number should be higher than the bottom number.")
        return cleaned


class AppointmentRequestForm(forms.Form):
    doctor = forms.ModelChoiceField(
        queryset=DoctorProfile.objects.all(),
        empty_label="Choose your Doctor",
        widget=forms.Select(attrs={'class': 'form-select'}),
        error_messages={'required': "Choose a doctor.", 'invalid_choice': "Choose a doctor from the list."},
    )
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        error_messages={'required': "Choose a date.", 'invalid': "Enter a valid date."},
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        error_messages={'required': "Choose a time.", 'invalid': "Enter a valid time."},
    )
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'E.g., Routine 2nd trimester ultrasound, recurring back pain, etc.'
        }),
        error_messages={'required': "Tell your doctor the reason for the visit.",
                        'max_length': "Keep the reason under 500 characters."},
    )

    def __init__(self, *args, mother=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.mother = mother

    @staticmethod
    def _taken(doctor, when):
        """True if the doctor already has a confirmed visit in that slot."""
        return Appointment.objects.filter(
            doctor=doctor, status__in=BOOKED,
            scheduled_datetime__gt=when - SLOT, scheduled_datetime__lt=when + SLOT,
        ).exists()

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time = cleaned_data.get('appointment_time')
        doctor = cleaned_data.get('doctor')
        if not (date and time):
            return cleaned_data

        when = timezone.make_aware(datetime.combine(date, time))
        cleaned_data['scheduled_datetime'] = when

        if when <= timezone.now():
            self.add_error('appointment_date', "Choose a date and time in the future.")
            return cleaned_data

        # The mother can't hold two requests for the same time.
        if self.mother and Appointment.objects.filter(
            mother=self.mother, status__in=BOOKED + ('Pending',),
            scheduled_datetime__gt=when - SLOT, scheduled_datetime__lt=when + SLOT,
        ).exists():
            self.add_error('appointment_time', "You already have a visit requested around that time.")
            return cleaned_data

        # The doctor's slot must be free. Suggest the next one that is.
        if doctor and self._taken(doctor, when):
            suggestion = when
            for _ in range(16):
                suggestion += SLOT
                if not self._taken(doctor, suggestion):
                    break
            local = timezone.localtime(suggestion)
            same_day = local.date() == date
            self.add_error(
                'appointment_time',
                "That time is already booked. The next free time is "
                f"{local.strftime('%I:%M %p').lstrip('0')}"
                f"{'' if same_day else local.strftime(' on %b %d')}."
            )
        return cleaned_data