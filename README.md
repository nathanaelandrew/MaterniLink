# MaterniLink: Your Digital Pregnancy Companion

MaterniLink is a web app that keeps pregnant mothers and their doctors connected throughout the pregnancy. Mothers track their health and baby's progress, request appointments and see their records; doctors manage requests, patients, prescriptions, tests and clinical notes in one place.

> **Student prototype.** MaterniLink was built for a university course. It does not replace professional medical care or emergency services.

## Features

**For mothers**
- Dashboard with pregnancy progress, "Baby this week", latest vitals and upcoming visits
- Health trends: weight, blood pressure, baby's heart rate and kick counts
- Kick counter and daily reminders
- Appointment requests, with cancelling while still pending
- Records: prescriptions, lab and ultrasound results, and uploads
- FAQ assistant (optional AI answers)

**For doctors**
- Dashboard with today's schedule and new requests
- Requests: accept, decline or reschedule appointments
- Patient index and full patient chart, including fetal heart rate
- Calendar, prescriptions, lab and ultrasound orders, and SOAP clinical notes

**For everyone**
- Messages between linked mothers and doctors, and notifications
- Profile, settings, and a Privacy Notice with sign-up consent

## Tech stack

- Python 3.12 and Django 6.1
- PostgreSQL on Supabase
- Bootstrap 5.3 (grid and dropdowns) plus a custom design system
- Server-rendered SVG charts, vanilla JavaScript

## Getting started

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/nathanaelandrew/MaterniLink.git
cd MaterniLink
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env              # Windows: copy .env.example .env
```

Then open `.env` and fill it in:

- **`SECRET_KEY`**: generate one with
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
  Paste it inside single quotes: `SECRET_KEY='...'`.
- **`DEBUG=True`** for local development.
- **Database values**: from Supabase, under **Connect → Session pooler** (port 5432, user `postgres.<project-ref>`). Ask a team member for the password.
- **`ANTHROPIC_API_KEY`** (optional): leave it empty to use the built-in FAQ answers only.

Never commit `.env`. It is already listed in `.gitignore`.

### 3. Set up the database and run

```bash
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and register as a mother or a doctor.

### 4. Run the tests

```bash
python manage.py test
```

## Project structure

```
apps/
  home/           dashboards, trends, kicks, reminders, records, messages, doctor pages
  profile/        models, profile, vitals, appointments, start tracking
  register/       sign-up
  login/          log in
  user_settings/  settings
maternilink/      project settings, URLs, landing and privacy pages
templates/        HTML templates
static/           CSS, JavaScript, images
```

## Notes

- Emails print in the `runserver` terminal (console backend).
- Uploaded files are saved in `media/` on the computer that receives them, and are only served to the owner and their linked doctor.
- Everyone who uses the same `.env` shares the same Supabase database.