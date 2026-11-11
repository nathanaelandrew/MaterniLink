from django.urls import path
from . import views, doctor_views, mother_views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kick-counter/', views.kick_counter, name='kick_counter'),

    # Mother tracking
    path('trends/', mother_views.trends, name='trends'),
    path('reminders/', mother_views.reminders, name='reminders'),
    path('reminders/<int:reminder_id>/toggle/', mother_views.reminder_toggle, name='reminder_toggle'),
    path('reminders/<int:reminder_id>/delete/', mother_views.reminder_delete, name='reminder_delete'),

    # Doctor side
    path('requests/', doctor_views.doctor_requests, name='doctor_requests'),
    path('requests/<int:appointment_id>/respond/', doctor_views.appointment_respond, name='appointment_respond'),
    path('patients/', doctor_views.doctor_patients, name='doctor_patients'),
    path('patients/<int:mother_id>/', doctor_views.doctor_patient_detail, name='doctor_patient_detail'),
    path('calendar/', doctor_views.doctor_calendar, name='doctor_calendar'),
]