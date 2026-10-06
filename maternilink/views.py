from django.shortcuts import render, redirect

def onboarding(request):
    if request.user.is_authenticated:
        return redirect('home:dashboard')
    return render(request, 'onboarding.html')