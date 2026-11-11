from django.urls import path
from . import views, doctor_views, mother_views, records_views

app_name = 'home'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kick-counter/', views.kick_counter, name='kick_counter'),

    # Mother tracking
    path('trends/', mother_views.trends, name='trends'),
    path('reminders/', mother_views.reminders, name='reminders'),
    path('reminders/<int:reminder_id>/toggle/', mother_views.reminder_toggle, name='reminder_toggle'),
    path('reminders/<int:reminder_id>/delete/', mother_views.reminder_delete, name='reminder_delete'),

    # Records
    path('records/', records_views.records, name='records'),
    path('records/upload/', records_views.record_upload, name='record_upload'),
    path('records/<int:record_id>/file/', records_views.record_file, name='record_file'),

    # Doctor side: lab / ultrasound requests, prescriptions, notes
    path('orders/', records_views.doctor_orders, name='doctor_orders'),
    path('orders/<int:order_id>/cancel/', records_views.order_cancel, name='order_cancel'),
    path('patients/<int:mother_id>/prescribe/', records_views.doctor_prescribe, name='doctor_prescribe'),
    path('patients/<int:mother_id>/upload/', records_views.doctor_upload, name='doctor_upload'),
    path('appointments/<int:appointment_id>/note/', records_views.doctor_note, name='doctor_note'),

    # Doctor side
    path('requests/', doctor_views.doctor_requests, name='doctor_requests'),
    path('requests/<int:appointment_id>/respond/', doctor_views.appointment_respond, name='appointment_respond'),
    path('patients/', doctor_views.doctor_patients, name='doctor_patients'),
    path('patients/<int:mother_id>/', doctor_views.doctor_patient_detail, name='doctor_patient_detail'),
    path('calendar/', doctor_views.doctor_calendar, name='doctor_calendar'),
]