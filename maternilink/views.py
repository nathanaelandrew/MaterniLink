from django.shortcuts import render, redirect

# Change the version (a date) whenever the Privacy Notice changes.
PRIVACY_VERSION = '2026-11-24'
# TODO: put the team's real contact email here.
PRIVACY_CONTACT_EMAIL = 'maternilink.team@example.com'


def onboarding(request):
    if request.user.is_authenticated:
        return redirect('home:dashboard')
    return render(request, 'onboarding.html')


def privacy_notice(request):
    """Public page: anyone can read it before signing up."""
    return render(request, 'privacy.html', {
        'privacy_version': PRIVACY_VERSION,
        'privacy_contact_email': PRIVACY_CONTACT_EMAIL,
    })