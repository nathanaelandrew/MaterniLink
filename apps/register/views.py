from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RegisterForm

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('login:login')
    else:
        form = RegisterForm()
    return render(request, 'register/register.html', {'form': form})