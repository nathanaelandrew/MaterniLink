from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpForm(UserCreationForm):
    ROLE_CHOICES = (
        ('Mother', 'Mother / Expectant Parent'),
        ('Doctor', 'Healthcare Provider / Doctor'),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    # Rendered as two selectable cards in register.html (RadioSelect keeps it
    # working without JavaScript and keeps the same field name: "role").
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        initial='Mother',
        widget=forms.RadioSelect(attrs={'class': 'role__input'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply form-control styling to username and password inputs
        for name, field in self.fields.items():
            if name != 'role':
                field.widget.attrs.update({'class': 'form-control'})

        self.fields['username'].widget.attrs.update({
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
        })
        self.fields['email'].widget.attrs.update({'autocomplete': 'email'})
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'At least 8 characters',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Repeat password',
            'autocomplete': 'new-password',
        })