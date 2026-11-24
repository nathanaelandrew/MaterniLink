"""Prints the SQL that Django generates for the JOIN and SUBQUERY features.

Usage:
    python manage.py show_sql                    # uses the first doctor
    python manage.py show_sql --doctor sqltest   # a doctor's username
"""
import sqlparse
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Subquery
from django.utils import timezone

from apps.home.doctor_views import CONFIRMED, patients_of
from apps.profile.models import Appointment, DoctorProfile


class Command(BaseCommand):
    help = "Show the SQL behind the JOIN (Requests page) and SUBQUERY (Patients > No upcoming visit)."

    def add_arguments(self, parser):
        parser.add_argument('--doctor', help="Username of the doctor to use")

    def handle(self, *args, **options):
        doctors = DoctorProfile.objects.filter(user__role='Doctor')
        if options['doctor']:
            doctor = doctors.filter(user__username=options['doctor']).first()
            if not doctor:
                raise CommandError(f"No doctor with username '{options['doctor']}'.")
        else:
            doctor = doctors.first()
            if not doctor:
                raise CommandError("There are no doctor accounts yet.")

        def show(title, queryset, rows):
            self.stdout.write(self.style.SUCCESS(f"\n{'=' * 70}\n{title}\n{'=' * 70}"))
            self.stdout.write(sqlparse.format(str(queryset.query), reindent=True, keyword_case='upper'))
            self.stdout.write(self.style.WARNING("\nResults:"))
            for line in rows or ["(no rows)"]:
                self.stdout.write(f"  {line}")

        self.stdout.write(f"Doctor: {doctor.user.username} (doctor_id {doctor.pk})")

        # 1. JOIN: appointments together with the patient's details
        join_qs = Appointment.objects.filter(doctor=doctor).select_related('mother').order_by('scheduled_datetime')
        show(
            "1. JOIN  -  Requests page: appointments with patient names",
            join_qs,
            [f"appointment {a.pk}: {a.mother.first_name} {a.mother.last_name} | "
             f"{timezone.localtime(a.scheduled_datetime):%b %d, %I:%M %p} | {a.status}"
             for a in join_qs],
        )

        # 2. SUBQUERY: patients with no upcoming confirmed visit
        inner = Appointment.objects.filter(
            doctor=doctor, status__in=CONFIRMED, scheduled_datetime__gte=timezone.now(),
        ).values('mother_id')
        sub_qs = patients_of(doctor).exclude(mother_id__in=Subquery(inner))
        show(
            "2. SUBQUERY  -  Patients > No upcoming visit",
            sub_qs,
            [f"mother {m.pk}: {m.first_name} {m.last_name}" for m in sub_qs],
        )
        self.stdout.write("")