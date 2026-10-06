from django.contrib import admin
from django.urls import path, include
from .views import onboarding  # Import the new landing view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. The Root Landing Page
    path('', onboarding, name='onboarding'),

    # 2. Namespaced Apps (Fixes the button logic)
    path('home/', include(('apps.home.urls', 'home'), namespace='home')),
    path('login/', include(('apps.login.urls', 'login'), namespace='login')),
    path('register/', include(('apps.register.urls', 'register'), namespace='register')),
    path('profile/', include(('apps.profile.urls', 'profile'), namespace='profile')),
    path('settings/', include(('apps.user_settings.urls', 'user_settings'), namespace='user_settings')),
]