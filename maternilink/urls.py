from django.contrib import admin
from django.urls import path, include
from .views import onboarding, privacy_notice  # Landing page and Privacy Notice

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. The Root Landing Page
    path('', onboarding, name='onboarding'),
    path('privacy/', privacy_notice, name='privacy'),

    # 2. Namespaced Apps (Fixes the button logic)
    path('home/', include(('apps.home.urls', 'home'), namespace='home')),
    path('login/', include(('apps.login.urls', 'login'), namespace='login')),
    path('register/', include(('apps.register.urls', 'register'), namespace='register')),
    path('profile/', include(('apps.profile.urls', 'profile'), namespace='profile')),
    path('settings/', include(('apps.user_settings.urls', 'user_settings'), namespace='user_settings')),
]