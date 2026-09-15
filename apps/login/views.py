from django.contrib.auth import views as auth_views

class LoginFeatureView(auth_views.LoginView):
    template_name = 'login/login.html'