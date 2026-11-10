from django import forms
from .models import MaternalHealthLog
from datetime import datetime
from .models import Appointment, DoctorProfile

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
        
class AppointmentRequestForm(forms.Form):
    doctor = forms.ModelChoiceField(
        queryset=DoctorProfile.objects.all(),
        empty_label="Choose your Doctor",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    appointment_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'E.g., Routine 2nd trimester ultrasound, recurring back pain, etc.'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time = cleaned_data.get('appointment_time')
        if date and time:
            cleaned_data['scheduled_datetime'] = datetime.combine(date, time)
        return cleaned_data