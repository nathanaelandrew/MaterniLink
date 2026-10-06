from django import forms
from .models import MaternalHealthLog

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