import os

from django import forms

from apps.profile.models import ClinicalNote, MedicalOrderRequest, MotherProfile, Prescription

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