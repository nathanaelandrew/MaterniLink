"""Records: prescriptions, lab/ultrasound requests and results, clinical notes."""
import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.profile.models import (
    Appointment,
    ClinicalNote,
    DoctorProfile,
    MedicalOrderRequest,
    MedicalRecord,
    MotherProfile,
    PregnancyProfile,
    Prescription,
)

from .doctor_views import CONFIRMED, doctor_required, patients_of
from .mother_views import mother_required
from .records_forms import (
    ClinicalNoteForm,
    OrderForm,
    PrescriptionForm,
    RecordUploadForm,
)

OPEN = 'Requested'


def ongoing_pregnancy(mother):
    return PregnancyProfile.objects.filter(
        mother=mother, pregnancy_status='Ongoing'
    ).order_by('-created_at').first()


def _save_upload(request, pregnancy, form, order):
    """Shared by the mother and doctor upload pages."""
    f = form.cleaned_data['file']
    record = MedicalRecord.objects.create(
        pregnancy=pregnancy,
        request=order,
        uploaded_by_user=request.user,
        record_type=order.request_type if order else form.cleaned_data['record_type'],
        summary_notes=form.cleaned_data['summary_notes'],
        file=f,
        original_name=os.path.basename(f.name)[:255],
    )
    if order and order.status == OPEN:
        order.status = 'Completed'
        order.save(update_fields=['status'])
    return record


# --------------------------------------------------------------------------
# Mother: records page and upload
# --------------------------------------------------------------------------
@mother_required
def records(request, mother):
    pregnancy = ongoing_pregnancy(mother)
    tab = request.GET.get('tab', 'prescriptions')
    if tab not in ('prescriptions', 'labs', 'ultrasound'):
        tab = 'prescriptions'

    prescriptions, files, open_orders = [], [], []
    if pregnancy:
        prescriptions = list(Prescription.objects.filter(pregnancy=pregnancy)
                             .select_related('doctor').order_by('-prescribed_date', '-pk'))
        files = list(MedicalRecord.objects.filter(pregnancy=pregnancy)
                     .select_related('uploaded_by_user', 'request').order_by('-uploaded_at'))
        open_orders = list(MedicalOrderRequest.objects.filter(pregnancy=pregnancy, status=OPEN)
                           .select_related('doctor').order_by('-requested_at'))

    labs = [r for r in files if r.record_type == 'Laboratory']
    scans = [r for r in files if r.record_type == 'Ultrasound']
    shown = {'prescriptions': prescriptions, 'labs': labs, 'ultrasound': scans}[tab]

    return render(request, 'home/records.html', {
        'mother': mother, 'pregnancy': pregnancy, 'tab': tab, 'items': shown,
        'counts': {'prescriptions': len(prescriptions), 'labs': len(labs), 'ultrasound': len(scans)},
        'open_orders': open_orders,
    })


def _order_from_query(request, pregnancy, doctor=None):
    """?request=<id> pre-selects an open request that belongs to this pregnancy."""
    try:
        oid = int(request.GET.get('request') or request.POST.get('request_id') or 0)
    except ValueError:
        return None
    qs = MedicalOrderRequest.objects.filter(pk=oid, pregnancy=pregnancy, status=OPEN)
    if doctor:
        qs = qs.filter(doctor=doctor)
    return qs.first()


@mother_required
def record_upload(request, mother):
    pregnancy = ongoing_pregnancy(mother)
    if not pregnancy:
        messages.error(request, "Start your pregnancy profile before adding records.")
        return redirect('home:records')

    order = _order_from_query(request, pregnancy)
    form = RecordUploadForm(request.POST or None, request.FILES or None,
                            initial={'record_type': order.request_type if order else 'Laboratory'})
    if request.method == 'POST' and form.is_valid():
        record = _save_upload(request, pregnancy, form, order)
        messages.success(request, "Result uploaded.")
        return redirect(f"{reverse('home:records')}?tab={'ultrasound' if record.record_type == 'Ultrasound' else 'labs'}")

    return render(request, 'home/record_upload.html', {
        'form': form, 'order': order,
        'back_url': reverse('home:records'),
        'heading': 'Add a result',
        'lead': "Upload a lab or ultrasound report as a PDF, JPG or PNG (up to 10 MB).",
    })


# --------------------------------------------------------------------------
# Private file download (the only way uploaded files are served)
# --------------------------------------------------------------------------
@login_required
def record_file(request, record_id):
    record = get_object_or_404(MedicalRecord.objects.select_related('pregnancy__mother'), pk=record_id)
    mother = record.pregnancy.mother

    allowed = mother.user_id == request.user.pk
    if not allowed and request.user.role == 'Doctor':
        doctor = DoctorProfile.objects.filter(user=request.user).first()
        allowed = bool(doctor) and patients_of(doctor).filter(pk=mother.pk).exists()
    if not allowed or not record.file:
        raise Http404

    name = record.original_name or os.path.basename(record.file.name)
    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    try:
        response = FileResponse(record.file.open('rb'), content_type=content_type,
                                as_attachment=request.GET.get('download') == '1', filename=name)
    except FileNotFoundError:
        raise Http404
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


# --------------------------------------------------------------------------
# Doctor: lab and ultrasound requests
# --------------------------------------------------------------------------
def _patients_with_pregnancy(doctor):
    return patients_of(doctor).filter(
        pregnancyprofile__pregnancy_status='Ongoing'
    ).distinct().order_by('last_name', 'first_name')


@doctor_required
def doctor_orders(request, doctor):
    patients = _patients_with_pregnancy(doctor)
    initial = {}
    try:
        pre = int(request.GET.get('patient') or 0)
        if patients.filter(pk=pre).exists():
            initial['patient'] = pre
    except ValueError:
        pass

    form = OrderForm(request.POST or None, patients=patients, initial=initial)
    if request.method == 'POST' and form.is_valid():
        mother = form.cleaned_data['patient']
        MedicalOrderRequest.objects.create(
            pregnancy=ongoing_pregnancy(mother), doctor=doctor,
            request_type=form.cleaned_data['request_type'],
            test_name=form.cleaned_data['test_name'].strip(),
            instructions=form.cleaned_data['instructions'].strip(),
            status=OPEN,
        )
        messages.success(request, f"{form.cleaned_data['request_type']} request sent to {mother.first_name}.")
        return redirect('home:doctor_orders')

    tab = request.GET.get('tab', 'open')
    base = MedicalOrderRequest.objects.filter(doctor=doctor).select_related('pregnancy__mother')
    open_qs = base.filter(status=OPEN).order_by('-requested_at')
    closed_qs = base.exclude(status=OPEN).order_by('-requested_at')
    tab = tab if tab in ('open', 'closed') else 'open'
    orders = list(open_qs if tab == 'open' else closed_qs)
    for o in orders:
        o.result = o.medicalrecord_set.order_by('-uploaded_at').first()

    return render(request, 'home/doctor_orders.html', {
        'doctor': doctor, 'form': form, 'orders': orders, 'tab': tab,
        'counts': {'open': open_qs.count(), 'closed': closed_qs.count()},
        'has_patients': patients.exists(),
    })


@doctor_required
@require_POST
def order_cancel(request, doctor, order_id):
    order = get_object_or_404(MedicalOrderRequest, pk=order_id, doctor=doctor)
    if order.status == OPEN:
        order.status = 'Cancelled'
        order.save(update_fields=['status'])
        messages.success(request, "Request cancelled.")
    return redirect('home:doctor_orders')


# --------------------------------------------------------------------------
# Doctor: prescriptions, uploads and clinical notes (all start from a patient)
# --------------------------------------------------------------------------
def _patient_and_pregnancy(request, doctor, mother_id):
    mother = get_object_or_404(patients_of(doctor), pk=mother_id)
    return mother, ongoing_pregnancy(mother)


@doctor_required
def doctor_prescribe(request, doctor, mother_id):
    mother, pregnancy = _patient_and_pregnancy(request, doctor, mother_id)
    back = reverse('home:doctor_patient_detail', args=[mother.pk])
    if not pregnancy:
        messages.error(request, f"{mother.first_name} has no active pregnancy yet.")
        return redirect(back)

    form = PrescriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        rx = form.save(commit=False)
        rx.pregnancy, rx.doctor, rx.prescribed_date = pregnancy, doctor, timezone.localdate()
        rx.save()
        messages.success(request, f"Prescription for {rx.medication_name} saved.")
        return redirect(back)

    return render(request, 'home/doctor_prescribe.html', {
        'doctor': doctor, 'patient': mother, 'form': form, 'back_url': back,
    })


@doctor_required
def doctor_upload(request, doctor, mother_id):
    mother, pregnancy = _patient_and_pregnancy(request, doctor, mother_id)
    back = reverse('home:doctor_patient_detail', args=[mother.pk])
    if not pregnancy:
        messages.error(request, f"{mother.first_name} has no active pregnancy yet.")
        return redirect(back)

    order = _order_from_query(request, pregnancy, doctor)
    form = RecordUploadForm(request.POST or None, request.FILES or None,
                            initial={'record_type': order.request_type if order else 'Laboratory'})
    if request.method == 'POST' and form.is_valid():
        _save_upload(request, pregnancy, form, order)
        messages.success(request, "Result added to the patient's record.")
        return redirect(back)

    return render(request, 'home/record_upload.html', {
        'doctor': doctor, 'patient': mother, 'form': form, 'order': order, 'back_url': back,
        'heading': f"Add a result for {mother.first_name}",
        'lead': "Attach a lab or ultrasound report (PDF, JPG or PNG, up to 10 MB).",
    })


@doctor_required
def doctor_note(request, doctor, appointment_id):
    appt = get_object_or_404(Appointment.objects.select_related('mother'), pk=appointment_id, doctor=doctor)
    back = reverse('home:doctor_patient_detail', args=[appt.mother_id])

    if appt.status not in CONFIRMED:
        messages.error(request, "Notes can be added once the appointment is accepted.")
        return redirect(back)
    pregnancy = ongoing_pregnancy(appt.mother)
    if not pregnancy:
        messages.error(request, f"{appt.mother.first_name} has no active pregnancy yet.")
        return redirect(back)

    note = ClinicalNote.objects.filter(appointment=appt, doctor=doctor).first()
    form = ClinicalNoteForm(request.POST or None, instance=note)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.appointment, obj.pregnancy, obj.doctor = appt, pregnancy, doctor
        obj.save()
        messages.success(request, "Clinical note saved.")
        return redirect(back)

    return render(request, 'home/doctor_note.html', {
        'doctor': doctor, 'patient': appt.mother, 'appt': appt,
        'form': form, 'editing': note is not None, 'back_url': back,
    })