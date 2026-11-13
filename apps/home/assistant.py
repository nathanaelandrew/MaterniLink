"""The pregnancy FAQ assistant.

Answers come from a built-in FAQ. If ANTHROPIC_API_KEY is set, questions are
answered by an AI model instead, with the FAQ as its reference, and the FAQ
is used again if the AI call fails. Urgent symptoms never go to the AI: they
always get a fixed "seek care now" reply.

Privacy: only the question and the recent chat turns are sent to the AI
service. No name, record, vitals or other patient data is included.
"""
import json
import re
import urllib.error
import urllib.request

from django.conf import settings

DISCLAIMER = ("This assistant gives general information only. It is not medical advice and "
              "cannot diagnose. For anything about your own health, ask your doctor. "
              "In an emergency, go to the nearest hospital.")

URGENT_REPLY = ("This could need urgent attention. Please contact your doctor or go to the nearest "
                "emergency room now. Don't wait for a reply here.")

CRISIS_REPLY = ("I'm really sorry you're feeling this way, and I'm glad you said something. You deserve "
                "support right now. Please reach out to someone you trust and to your doctor today. If you "
                "might act on these thoughts, call your local emergency number or go to the nearest "
                "emergency room now.")

URGENT_PATTERNS = [
    r'\bbleed', r'\bblood\b', r'severe (pain|headache|cramp)', r"can'?t breathe", r'short(ness)? of breath',
    r'chest pain', r'\bfaint', r'passed out', r'seizure', r'convuls', r'waters? (broke|breaking|has broken)',
    r'leaking fluid', r'(not|stopped|no longer) moving', r'no (movement|kicks)', r'(less|fewer|reduced|decreased) (movement|kicks|moving)',
    r'blurr?(ed|y) vision', r'high fever', r'emergency',
]
CRISIS_PATTERNS = [r'suicid', r'kill myself', r'harm myself', r'hurt myself', r'end my life', r"don'?t want to live"]

# (keywords, answer). The first entry with the most keyword hits wins.
FAQ = [
    (['appointment', 'book', 'schedule', 'visit', 'check-up', 'checkup'],
     "To book a visit, open Appointments, choose your doctor, a date and a time, and add the reason. "
     "Your doctor can accept, decline or move the visit, and you will get a notification when they respond."),
    (['kick', 'movement', 'moving', 'count'],
     "Many doctors suggest paying attention to your baby's movements from around 28 weeks. A common method "
     "is to note how long it takes to feel 10 movements at a time of day when your baby is usually active. "
     "You can record a session on the Kicks page. If your baby is moving much less than usual, contact your "
     "doctor right away rather than waiting until the next day."),
    (['blood pressure', 'bp', 'vitals', 'hypertension'],
     "You can log your blood pressure and weight with Record vitals and see the chart under Trends. "
     "In pregnancy, a reading of 140/90 or higher is considered high and should be reported to your doctor. "
     "A reading of 160/110 or higher needs medical attention the same day."),
    (['weight', 'gain'],
     "Healthy weight gain in pregnancy depends on your weight before pregnancy, so there isn't one number "
     "for everyone. Your doctor can tell you the range that suits you. You can track your weight with "
     "Record vitals and see it over time under Trends."),
    (['coffee', 'caffeine', 'tea'],
     "Most guidance suggests keeping caffeine to about 200 mg a day in pregnancy, which is roughly one to "
     "two cups of coffee. Remember that tea, soft drinks and chocolate contain caffeine too."),
    (['eat', 'food', 'diet', 'nutrition', 'avoid', 'meal'],
     "Aim for regular, balanced meals with vegetables, fruit, whole grains and protein, and drink plenty of "
     "water. It is generally advised to avoid alcohol, raw or undercooked meat, fish and eggs, unpasteurised "
     "milk and cheese, and fish that is high in mercury. Your doctor can give advice that fits you."),
    (['vitamin', 'folic', 'iron', 'supplement', 'calcium'],
     "Prenatal vitamins usually include folic acid and iron, which support your baby's development and your "
     "blood supply. Take the supplements your doctor recommends, in the amounts they prescribe. Anything they "
     "prescribe in MaterniLink appears under Records."),
    (['medicine', 'medication', 'drug', 'paracetamol', 'ibuprofen', 'antibiotic', 'pill', 'safe to take'],
     "Some medicines are not safe in pregnancy, including some sold without a prescription. Check with your "
     "doctor or pharmacist before taking anything new, and don't stop a prescribed medicine without asking them."),
    (['exercise', 'workout', 'walk', 'yoga', 'swim', 'gym'],
     "For most pregnancies, regular moderate activity such as walking, swimming or prenatal yoga is safe and "
     "helpful, unless your doctor has told you otherwise. Avoid contact sports and activities with a risk of "
     "falling. Stop and contact your doctor if you feel dizzy, have pain, or notice bleeding."),
    (['nausea', 'vomit', 'morning sickness', 'sick'],
     "Nausea is common, especially in the first trimester. Small, frequent meals, plain foods and sipping "
     "fluids through the day can help. If you can't keep food or fluids down, contact your doctor."),
    (['sleep', 'back pain', 'backache', 'tired', 'fatigue'],
     "Tiredness and back discomfort are common. Rest when you can, and later in pregnancy many doctors "
     "recommend sleeping on your side, with a pillow between your knees for comfort. Tell your doctor about "
     "pain that is strong or doesn't ease."),
    (['swelling', 'swollen', 'edema'],
     "Mild swelling of the feet and ankles is common later in pregnancy. Sudden swelling of the face or "
     "hands, especially with a headache or vision changes, should be reported to your doctor straight away."),
    (['labor', 'labour', 'contraction'],
     "Signs of labour include contractions that become regular, stronger and closer together, and your "
     "waters breaking. Contact your doctor or hospital when this starts, or sooner if they told you to."),
    (['warning', 'danger', 'call my doctor', 'call the doctor', 'worried'],
     "Contact your doctor straight away for bleeding, leaking fluid, severe headache, blurred vision, sudden "
     "swelling, strong belly pain, fever, or if your baby is moving much less than usual."),
    (['due date', 'how many weeks', 'trimester', 'weeks', 'how far'],
     "Pregnancy is counted as about 40 weeks from the first day of your last period, in three trimesters: "
     "weeks 1 to 13, 14 to 27, and 28 to 40. Your dashboard shows your current week and trimester."),
    (['reminder'],
     "Open Reminders to add daily reminders for medication, check-ups, meals and exercise. Tick each one off "
     "when it's done; they reset the next day."),
    (['record', 'upload', 'lab', 'ultrasound', 'result', 'prescription'],
     "Your prescriptions and your lab and ultrasound results are under Records. Use Add a result to upload "
     "a report as a PDF or photo. If your doctor requested a test, it appears at the top with an Upload button."),
    (['message', 'contact', 'talk to', 'chat with'],
     "Use Messages (the speech bubble at the top of the page) to write to a doctor you have a visit or "
     "pregnancy profile with. For anything urgent, call the clinic or go to the hospital instead."),
]

FALLBACK = ("I don't have a prepared answer for that. You could try asking about appointments, baby movements, "
            "blood pressure, food, vitamins, exercise or warning signs. For anything about your own health, "
            "please message your doctor.")

SUGGESTIONS = [
    "What foods should I avoid?",
    "How do I count my baby's kicks?",
    "What blood pressure is too high?",
    "Is exercise safe during pregnancy?",
    "When should I call my doctor?",
]


def _matches(patterns, text):
    return any(re.search(p, text) for p in patterns)


def faq_answer(question):
    text = question.lower()
    best, best_score = None, 0
    for keywords, answer in FAQ:
        score = sum(1 for k in keywords if re.search(r'\b' + re.escape(k), text))
        if score > best_score:
            best, best_score = answer, score
    return best


def _ai_answer(question, history):
    """Ask the AI model. Returns None on any problem so the caller can fall back."""
    key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not key:
        return None

    reference = "\n".join(f"- {answer}" for _, answer in FAQ)
    system = (
        "You are the MaterniLink assistant, a friendly helper inside a pregnancy companion web app. "
        "Answer questions about pregnancy, maternal health and how to use the app, in plain language, "
        "in under 120 words, with no markdown.\n"
        "Rules: give general information only. Never diagnose, never give medicine doses, and never "
        "contradict a doctor. For anything about the user's own situation, tell them to ask their doctor. "
        "If they describe a possibly urgent symptom, tell them to contact their doctor or go to the "
        "emergency room now. If the question is not about pregnancy, health or the app, politely say "
        "you can only help with those.\n"
        "Reference answers you should stay consistent with:\n" + reference
    )
    # The API needs alternating turns that start with the user.
    recent = [m for m in history if m.get('role') in ('user', 'assistant')][-6:]
    while recent and recent[0]['role'] != 'user':
        recent = recent[1:]
    messages = [{'role': m['role'], 'content': m['text']} for m in recent]
    messages.append({'role': 'user', 'content': question})

    body = json.dumps({
        'model': getattr(settings, 'CHATBOT_MODEL', 'claude-haiku-5-5'),
        'max_tokens': 400,
        'system': system,
        'messages': messages,
    }).encode()
    request = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=body, method='POST',
        headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read())
        text = ''.join(part.get('text', '') for part in data.get('content', []) if part.get('type') == 'text')
        return text.strip() or None
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None


def answer(question, history=()):
    """Returns {'text', 'urgent', 'source'} where source is 'safety', 'ai' or 'faq'."""
    text = question.lower()
    if _matches(CRISIS_PATTERNS, text):
        return {'text': CRISIS_REPLY, 'urgent': True, 'source': 'safety'}
    if _matches(URGENT_PATTERNS, text):
        return {'text': URGENT_REPLY, 'urgent': True, 'source': 'safety'}

    ai = _ai_answer(question, list(history))
    if ai:
        return {'text': ai, 'urgent': False, 'source': 'ai'}
    return {'text': faq_answer(question) or FALLBACK, 'urgent': False, 'source': 'faq'}