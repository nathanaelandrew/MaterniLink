import os

from django import forms
from django.utils import timezone

from apps.profile.models import ClinicalNote, FetalHealthLog, MedicalOrderRequest, MotherProfile, Prescription

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

RECORD_TYPES = [('Laboratory', 'Laboratory result'), ('Ultrasound', 'Ultrasound result')]


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['medication_name', 'dosage', 'frequency', 'duration', 'instructions']
        widgets = {
            'medication_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Ferrous sulfate'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 325 mg'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Once daily after breakfast'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3 months'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                  'placeholder': 'Anything the patient should know (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructions'].required = False


class OrderForm(forms.Form):
    """A lab or ultrasound request from a doctor."""
    patient = forms.ModelChoiceField(
        queryset=MotherProfile.objects.none(),
        empty_label='Choose a patient',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    request_type = forms.ChoiceField(
        choices=[('Laboratory', 'Laboratory'), ('Ultrasound', 'Ultrasound')],
        initial='Laboratory',
        widget=forms.RadioSelect,
    )
    test_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Complete blood count, or Anatomy scan'}),
    )
    instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Preparation, fasting, where to go (optional)'}),
    )

    def __init__(self, *args, patients=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patients is not None:
            self.fields['patient'].queryset = patients


class ClinicalNoteForm(forms.ModelForm):
    class Meta:
        model = ClinicalNote
        fields = ['subjective_notes', 'objective_findings', 'assessment', 'clinical_plan']
        labels = {
            'subjective_notes': 'Subjective',
            'objective_findings': 'Objective',
            'assessment': 'Assessment',
            'clinical_plan': 'Plan',
        }
        widgets = {
            'subjective_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                      'placeholder': 'What the patient reports: symptoms, concerns, history'}),
            'objective_findings': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                        'placeholder': 'Exam findings, vitals, measurements'}),
            'assessment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                'placeholder': 'Your clinical impression'}),
            'clinical_plan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                   'placeholder': 'Treatment, orders, advice and follow-up'}),
        }


class RecordUploadForm(forms.Form):
    record_type = forms.ChoiceField(choices=RECORD_TYPES, widget=forms.RadioSelect, initial='Laboratory')
    summary_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'A short note about this result (optional)'}),
    )
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={
        'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'}))

    def clean_file(self):
        f = self.cleaned_data['file']
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
        if f.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("The file is larger than 10 MB.")
        if f.size == 0:
            raise forms.ValidationError("The file is empty.")
        return f

class FetalCheckForm(forms.ModelForm):
    """Baby's heart rate (and optional fundal height), recorded by the doctor."""
    class Meta:
        model = FetalHealthLog
        fields = ['recorded_date', 'fetal_heart_rate_bpm', 'fundal_height_cm']
        labels = {
            'recorded_date': 'Date measured',
            'fetal_heart_rate_bpm': 'Fetal heart rate (bpm)',
            'fundal_height_cm': 'Fundal height (cm)',
        }
        widgets = {
            'recorded_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fetal_heart_rate_bpm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 145',
                                                             'min': 60, 'max': 240, 'inputmode': 'numeric'}),
            'fundal_height_cm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional, e.g. 24.5',
                                                         'min': 5, 'max': 50, 'step': '0.1', 'inputmode': 'decimal'}),
        }

    def __init__(self, *args, pregnancy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pregnancy = pregnancy
        self.fields['fundal_height_cm'].required = False
        if not self.is_bound and not self.initial.get('recorded_date'):
            self.initial['recorded_date'] = timezone.localdate()

    def clean_recorded_date(self):
        d = self.cleaned_data['recorded_date']
        if d > timezone.localdate():
            raise forms.ValidationError("The date can't be in the future.")
        if self.pregnancy and d < self.pregnancy.lmp_date:
            raise forms.ValidationError("The date is before this pregnancy started.")
        if self.pregnancy and (d - self.pregnancy.lmp_date).days < 6 * 7:
            raise forms.ValidationError("A heartbeat can't usually be measured before 6 weeks. Check the date.")
        return d

    def clean_fetal_heart_rate_bpm(self):
        bpm = self.cleaned_data['fetal_heart_rate_bpm']
        if not 60 <= bpm <= 240:
            raise forms.ValidationError("Enter a heart rate between 60 and 240 bpm.")
        return bpm

    def clean_fundal_height_cm(self):
        cm = self.cleaned_data.get('fundal_height_cm')
        if cm is not None and not 5 <= cm <= 50:
            raise forms.ValidationError("Enter a fundal height between 5 and 50 cm, or leave it blank.")
        return cm