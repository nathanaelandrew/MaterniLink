from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import MotherProfile, PregnancyProfile, User
from .utils import calculate_edd, gestational_progress


class PregnancyMathTests(TestCase):
    def test_edd_is_280_days_after_lmp(self):
        self.assertEqual(calculate_edd(date(2026, 1, 1)), date(2026, 10, 8))

    def test_progress_weeks_days_and_trimesters(self):
        lmp = date(2026, 1, 1)
        p = gestational_progress(lmp, lmp + timedelta(days=100))  # 14w2d
        self.assertEqual((p['weeks'], p['days'], p['trimester']), (14, 2, 2))
        self.assertEqual(gestational_progress(lmp, lmp + timedelta(days=90))['trimester'], 1)   # 12w6d
        self.assertEqual(gestational_progress(lmp, lmp + timedelta(days=196))['trimester'], 3)  # 28w0d

    def test_progress_is_capped_and_never_negative(self):
        lmp = date(2026, 1, 1)
        late = gestational_progress(lmp, lmp + timedelta(days=290))
        self.assertEqual(late['percent'], 100)
        self.assertLess(late['days_to_go'], 0)
        self.assertEqual(gestational_progress(lmp, lmp - timedelta(days=5))['weeks'], 0)


class StartPregnancyFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mom', 'mom@example.com', 'pw-12345-xyz', role='Mother')
        self.mother = MotherProfile.objects.create(user=self.user, date_of_birth='1998-05-01')
        self.client.force_login(self.user)
        self.url = reverse('profile:start_pregnancy')
        self.today = timezone.localdate()

    def _post(self, lmp):
        return self.client.post(self.url, {'lmp_date': lmp.isoformat()})

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_page_renders(self):
        self.assertContains(self.client.get(self.url), 'Start Tracking')

    def test_valid_lmp_creates_pregnancy_with_edd(self):
        lmp = self.today - timedelta(days=70)
        response = self._post(lmp)
        self.assertRedirects(response, reverse('home:dashboard'))
        preg = PregnancyProfile.objects.get(mother=self.mother)
        self.assertEqual(preg.lmp_date, lmp)
        self.assertEqual(preg.edd_date, lmp + timedelta(days=280))
        self.assertEqual(preg.pregnancy_status, 'Ongoing')
        self.assertIsNone(preg.doctor)

    def test_future_lmp_is_rejected(self):
        response = self._post(self.today + timedelta(days=1))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['lmp_date'])
        self.assertFalse(PregnancyProfile.objects.exists())

    def test_lmp_older_than_42_weeks_is_rejected(self):
        response = self._post(self.today - timedelta(days=295))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PregnancyProfile.objects.exists())

    def test_cannot_start_second_ongoing_pregnancy(self):
        self._post(self.today - timedelta(days=30))
        response = self._post(self.today - timedelta(days=60))
        self.assertRedirects(response, reverse('home:dashboard'))
        self.assertEqual(PregnancyProfile.objects.filter(mother=self.mother).count(), 1)

    def test_doctors_are_redirected_away(self):
        doc = User.objects.create_user('doc', 'doc@example.com', 'pw-12345-xyz', role='Doctor')
        self.client.force_login(doc)
        self.assertRedirects(self.client.get(self.url), reverse('home:dashboard'))


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mom', 'mom@example.com', 'pw-12345-xyz', role='Mother')
        self.mother = MotherProfile.objects.create(user=self.user, date_of_birth='1998-05-01')
        self.client.force_login(self.user)

    def test_empty_state_prompts_to_start_pregnancy(self):
        response = self.client.get(reverse('home:dashboard'))
        self.assertContains(response, reverse('profile:start_pregnancy'))
        self.assertNotContains(response, "Record Today's Vitals")

    def test_dashboard_shows_weeks_from_lmp(self):
        lmp = timezone.localdate() - timedelta(days=100)  # 14 weeks, 2 days
        PregnancyProfile.objects.create(
            mother=self.mother, lmp_date=lmp, edd_date=calculate_edd(lmp), pregnancy_status='Ongoing')
        response = self.client.get(reverse('home:dashboard'))
        self.assertEqual(response.context['weeks'], 14)
        self.assertEqual(response.context['trimester'], 2)
        self.assertContains(response, "Record Today's Vitals")
        self.assertNotContains(response, 'Set up my pregnancy')


class SignupRedirectTests(TestCase):
    def _register(self, role):
        return self.client.post(reverse('register:register'), {
            'username': f'user_{role.lower()}', 'email': f'{role.lower()}@example.com',
            'password1': 'Str0ngPass!234', 'password2': 'Str0ngPass!234', 'role': role,
        })

    def test_new_mother_lands_on_start_pregnancy(self):
        response = self._register('Mother')
        self.assertRedirects(response, reverse('profile:start_pregnancy'))
        self.assertTrue(MotherProfile.objects.filter(user__username='user_mother').exists())

    def test_new_doctor_lands_on_dashboard(self):
        self.assertRedirects(self._register('Doctor'), reverse('home:dashboard'))
