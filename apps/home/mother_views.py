"""Mother-side tracking: health trends and daily reminders."""
from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.profile.models import (
    KickCountLog,
    MaternalHealthLog,
    MotherProfile,
    PregnancyProfile,
    Reminder,
)

from .tracking import bar_chart, line_chart

KICK_GOAL = 10          # same goal the kick counter page uses
MAX_REMINDERS = 50
CATEGORIES = ['Medication', 'Check-up', 'Eating', 'Exercise']


def mother_required(view):
    """Only logged-in mothers get in. The view receives the MotherProfile."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role == 'Doctor':
            return redirect('home:dashboard')
        mother = MotherProfile.objects.filter(user=request.user).first()
        if not mother:
            # The profile page creates a starter profile for mothers.
            return redirect('profile:profile')
        return view(request, mother, *args, **kwargs)
    return wrapper


def bp_status(systolic, diastolic):
    """Gentle, informational classification of one blood pressure reading."""
    if systolic >= 160 or diastolic >= 110:
        return ('urgent', 'Very high',
                "Please contact your care team today. If you also have a bad headache, "
                "blurred vision or pain under your ribs, seek urgent care.")
    if systolic >= 140 or diastolic >= 90:
        return ('high', 'A little high',
                "Rest for a few minutes and measure again. If it stays this high, "
                "let your doctor know.")
    if systolic < 90 or diastolic < 60:
        return ('low', 'A little low',
                "Sit or lie down and drink some water. Mention it at your next visit "
                "if it keeps happening.")
    return ('ok', 'In the usual range', "Nothing unusual in your latest reading.")


# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------
@mother_required
def trends(request, mother):
    pregnancy = PregnancyProfile.objects.filter(
        mother=mother, pregnancy_status='Ongoing'
    ).order_by('-created_at').first()

    logs, sessions = [], []
    if pregnancy:
        logs = list(MaternalHealthLog.objects.filter(pregnancy=pregnancy)
                    .order_by('-log_date', '-pk')[:12])[::-1]
        sessions = list(KickCountLog.objects.filter(pregnancy=pregnancy)
                        .order_by('-start_time')[:10])[::-1]

    ctx = {'mother': mother, 'has_logs': bool(logs), 'has_sessions': bool(sessions),
           'kick_goal': KICK_GOAL}

    if logs:
        dates = [l.log_date for l in logs]
        weights = [float(l.weight_kg) for l in logs]
        ctx['weight_chart'] = line_chart(
            dates,
            [{'name': 'Weight', 'cls': 'sage', 'values': weights, 'unit': 'kg'}],
            min_span=4, area=True,
        )
        ctx['weight_latest'] = weights[-1]
        change = weights[-1] - weights[0]
        ctx['weight_change'] = f"{change:+.1f}" if len(weights) > 1 else None

        ctx['bp_chart'] = line_chart(
            dates,
            [
                {'name': 'Systolic', 'cls': 'sage', 'unit': 'mmHg',
                 'values': [l.systolic_bp for l in logs],
                 'flags': [l.systolic_bp >= 140 or l.systolic_bp < 90 for l in logs]},
                {'name': 'Diastolic', 'cls': 'clay', 'unit': 'mmHg',
                 'values': [l.diastolic_bp for l in logs],
                 'flags': [l.diastolic_bp >= 90 or l.diastolic_bp < 60 for l in logs]},
            ],
            refs=[(140, '140'), (90, '90')], min_span=40,
        )
        last = logs[-1]
        level, label, advice = bp_status(last.systolic_bp, last.diastolic_bp)
        ctx['bp_latest'] = f"{last.systolic_bp}/{last.diastolic_bp}"
        ctx['bp_level'], ctx['bp_label'], ctx['bp_advice'] = level, label, advice
        ctx['flagged_count'] = sum(
            1 for l in logs if bp_status(l.systolic_bp, l.diastolic_bp)[0] != 'ok'
        )
        ctx['log_count'] = len(logs)

    if sessions:
        local = timezone.localtime
        ctx['kick_chart'] = bar_chart(
            [(local(s.start_time).strftime('%b %d').replace(' 0', ' '), s.kick_count,
              f"{local(s.start_time).strftime('%b %d, %I:%M %p')}: "
              f"{s.kick_count} movements in {s.duration_minutes} min")
             for s in sessions],
            goal=KICK_GOAL, W=1000, H=300,
        )
        ctx['kick_avg'] = round(sum(s.kick_count for s in sessions) / len(sessions), 1)
        ctx['kick_goal_met'] = sum(1 for s in sessions if s.kick_count >= KICK_GOAL)
        ctx['kick_sessions'] = len(sessions)

    return render(request, 'home/trends.html', ctx)


# --------------------------------------------------------------------------
# Reminders
# --------------------------------------------------------------------------
def annotate_reminders(reminders):
    """Adds .done and .is_due (past its time today and not ticked off) to each."""
    today = timezone.localdate()
    now_t = timezone.localtime().time()
    items = list(reminders)
    for r in items:
        r.done = r.last_done == today
        r.is_due = (not r.done) and r.scheduled_time <= now_t
    return items


@mother_required
def reminders(request, mother):
    form, errors = {'category': 'Medication', 'title': '', 'time': ''}, {}

    if request.method == 'POST':
        form = {
            'category': request.POST.get('category', ''),
            'title': request.POST.get('title', '').strip(),
            'time': request.POST.get('time', '')[:5],
        }
        if form['category'] not in CATEGORIES:
            errors['category'] = "Choose a category."
        if not form['title']:
            errors['title'] = "Give the reminder a name."
        elif len(form['title']) > 120:
            errors['title'] = "Keep it under 120 characters."
        try:
            scheduled_time = datetime.strptime(form['time'], '%H:%M').time()
        except ValueError:
            errors['time'] = "Choose a time."
        if not errors and Reminder.objects.filter(mother=mother, is_active=True).count() >= MAX_REMINDERS:
            errors['title'] = f"You can have up to {MAX_REMINDERS} reminders."

        if not errors:
            Reminder.objects.create(
                mother=mother, reminder_type=form['category'], title=form['title'],
                scheduled_time=scheduled_time, frequency='Daily', is_active=True,
            )
            messages.success(request, "Reminder added.")
            return redirect('home:reminders')

    items = annotate_reminders(Reminder.objects.filter(mother=mother, is_active=True).order_by('scheduled_time', 'reminder_id'))
    return render(request, 'home/reminders.html', {
        'mother': mother,
        'reminders': items,
        'done_count': sum(1 for r in items if r.done),
        'total': len(items),
        'form': form,
        'errors': errors,
        'categories': CATEGORIES,
    })


def _back(request):
    return redirect('home:dashboard' if request.POST.get('return_to') == 'dashboard'
                    else 'home:reminders')


@mother_required
@require_POST
def reminder_toggle(request, mother, reminder_id):
    r = get_object_or_404(Reminder, pk=reminder_id, mother=mother, is_active=True)
    today = timezone.localdate()
    r.last_done = None if r.last_done == today else today
    r.save(update_fields=['last_done'])
    return _back(request)


@mother_required
@require_POST
def reminder_delete(request, mother, reminder_id):
    get_object_or_404(Reminder, pk=reminder_id, mother=mother, is_active=True).delete()
    messages.success(request, "Reminder removed.")
    return _back(request)