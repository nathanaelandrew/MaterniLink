"""Communication: messages, notifications and the FAQ assistant."""
import time

from django.contrib import messages as flash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.profile.models import DoctorProfile, Message, MotherProfile, Notification

from . import assistant as bot
from .doctor_views import patients_of

User = get_user_model()

MAX_MESSAGE_LENGTH = 2000
MAX_QUESTION_LENGTH = 500
CHAT_HISTORY_LIMIT = 30
CHAT_RATE_LIMIT = 30          # questions per hour, per session


# --------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------
def contacts_for(user):
    """People this user may message: a mother's doctors, or a doctor's patients."""
    people = {}
    if user.role == 'Doctor':
        doctor = DoctorProfile.objects.filter(user=user).first()
        if doctor:
            for m in patients_of(doctor):
                people[m.user_id] = {
                    'user_id': m.user_id,
                    'name': f"{m.first_name} {m.last_name}".strip(),
                    'sub': 'Patient',
                }
    else:
        mother = MotherProfile.objects.filter(user=user).first()
        if mother:
            doctors = DoctorProfile.objects.filter(
                Q(pregnancyprofile__mother=mother) | Q(appointment__mother=mother)
            ).distinct()
            for d in doctors:
                name = d.first_name if d.last_name == 'Doctor' else d.last_name
                people[d.user_id] = {
                    'user_id': d.user_id,
                    'name': f"Dr. {name}",
                    'sub': d.specialization,
                }
    people.pop(user.pk, None)   # never yourself
    return people


def _stamp(dt):
    return timezone.localtime(dt).strftime('%I:%M %p').lstrip('0')


def _conversation(user, other_id):
    return Message.objects.filter(
        Q(sender=user, receiver_id=other_id) | Q(sender_id=other_id, receiver=user)
    )


@login_required
def inbox(request, user_id=None):
    user = request.user
    people = contacts_for(user)
    if user_id is not None and user_id not in people:
        raise Http404

    if request.method == 'POST' and user_id is not None:
        body = request.POST.get('body', '').strip()
        if not body:
            flash.error(request, "Write a message first.")
        elif len(body) > MAX_MESSAGE_LENGTH:
            flash.error(request, f"Messages can be up to {MAX_MESSAGE_LENGTH} characters.")
        else:
            Message.objects.create(sender=user, receiver_id=user_id, message_body=body)
        return redirect('home:thread', user_id=user_id)

    # Last message and unread count per contact
    for p in people.values():
        p.update(last=None, unread=0)
    recent = Message.objects.filter(Q(sender=user) | Q(receiver=user)).order_by('-sent_at')[:500]
    for m in recent:
        other = m.receiver_id if m.sender_id == user.pk else m.sender_id
        p = people.get(other)
        if not p:
            continue
        if p['last'] is None:
            p['last'] = m
        if m.receiver_id == user.pk and not m.is_read:
            p['unread'] += 1
    contacts = sorted(people.values(),
                      key=lambda p: (p['last'].sent_at.timestamp() if p['last'] else 0, p['name']),
                      reverse=True)

    active, thread = None, []
    if user_id is not None:
        active = people[user_id]
        _conversation(user, user_id).filter(receiver=user, is_read=False).update(is_read=True)
        active['unread'] = 0
        thread = list(_conversation(user, user_id).order_by('-sent_at')[:100])[::-1]

    return render(request, 'home/messages.html', {
        'contacts': contacts, 'active': active, 'thread': thread,
        'last_id': thread[-1].pk if thread else 0,
        'max_length': MAX_MESSAGE_LENGTH,
    })


@login_required
def thread_poll(request, user_id):
    """New messages in a conversation since ?after=<id>, as JSON."""
    user = request.user
    if user_id not in contacts_for(user):
        raise Http404
    try:
        after = int(request.GET.get('after', 0))
    except ValueError:
        after = 0
    new = list(_conversation(user, user_id).filter(pk__gt=after).order_by('sent_at')[:50])
    Message.objects.filter(pk__in=[m.pk for m in new if m.receiver_id == user.pk]).update(is_read=True)
    return JsonResponse({'messages': [
        {'id': m.pk, 'body': m.message_body, 'mine': m.sender_id == user.pk, 'time': _stamp(m.sent_at)}
        for m in new
    ]})


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
@login_required
def notifications(request):
    items = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'home/notifications.html', {
        'items': items,
        'unread': Notification.objects.filter(user=request.user, is_read=False).count(),
    })


@login_required
def notification_open(request, notification_id):
    """Marks one notification read and goes to what it is about."""
    n = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    # Only ever redirect to a path inside this site.
    if n.link.startswith('/') and not n.link.startswith('//') and '\\' not in n.link:
        return redirect(n.link)
    return redirect('home:notifications')


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('home:notifications')


# --------------------------------------------------------------------------
# FAQ assistant
# --------------------------------------------------------------------------
def _rate_limited(session):
    now = time.time()
    stamps = [t for t in session.get('assistant_stamps', []) if now - t < 3600]
    if len(stamps) >= CHAT_RATE_LIMIT:
        session['assistant_stamps'] = stamps
        return True
    stamps.append(now)
    session['assistant_stamps'] = stamps
    return False


@login_required
def assistant(request):
    if request.user.role == 'Doctor':
        return redirect('home:dashboard')

    history = request.session.get('assistant_chat', [])
    wants_json = request.headers.get('X-Requested-With') == 'fetch'

    if request.method == 'POST':
        if request.POST.get('action') == 'clear':
            request.session['assistant_chat'] = []
            return redirect('home:assistant')

        question = ' '.join(request.POST.get('question', '').split())[:MAX_QUESTION_LENGTH]
        if not question:
            reply = {'text': "Type a question and I'll do my best to help.", 'urgent': False, 'source': 'faq'}
        elif _rate_limited(request.session):
            reply = {'text': "You've asked a lot of questions this hour. Please try again a little later, "
                             "or message your doctor.", 'urgent': False, 'source': 'faq'}
        else:
            reply = bot.answer(question, history)

        if question:
            history = history + [
                {'role': 'user', 'text': question},
                {'role': 'assistant', 'text': reply['text'], 'urgent': reply['urgent']},
            ]
            request.session['assistant_chat'] = history[-CHAT_HISTORY_LIMIT:]

        if wants_json:
            return JsonResponse({'reply': reply['text'], 'urgent': reply['urgent']})
        return redirect('home:assistant')

    return render(request, 'home/assistant.html', {
        'history': history,
        'suggestions': bot.SUGGESTIONS,
        'disclaimer': bot.DISCLAIMER,
        'max_length': MAX_QUESTION_LENGTH,
    })