from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from .models import UserSettings

User = get_user_model()


class EmailForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email']
        widgets = {'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'})}
        error_messages = {'email': {'invalid': "Enter a valid email address, like name@example.com."}}

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email:
            raise forms.ValidationError("Enter your email address.")
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email


@login_required
def settings_view(request):
    user = request.user
    prefs, _ = UserSettings.objects.get_or_create(user=user)

    email_form = EmailForm(instance=user)
    password_form = PasswordChangeForm(user)
    action = request.POST.get('action') if request.method == 'POST' else None

    if action == 'preferences':
        prefs.email_notifications = 'email_notifications' in request.POST
        prefs.reduce_motion = 'reduce_motion' in request.POST
        prefs.show_assistant = 'show_assistant' in request.POST
        prefs.save()
        messages.success(request, "Preferences saved.")
        return redirect('user_settings:settings')

    if action == 'email':
        email_form = EmailForm(request.POST, instance=user)
        if email_form.is_valid():
            email_form.save()
            messages.success(request, "Email updated.")
            return redirect('user_settings:settings')

    if action == 'password':
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)   # stay logged in
            messages.success(request, "Password changed.")
            return redirect('user_settings:settings')

    for field in password_form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})

    return render(request, 'user_settings/settings.html', {
        'prefs': prefs,
        'email_form': email_form,
        'password_form': password_form,
        'is_doctor': user.role == 'Doctor',
    })