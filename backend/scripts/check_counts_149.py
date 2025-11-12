import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import TestSession, TestAnswer


def normalize(s: str) -> str:
    if not s:
        return 'Other'
    s_low = s.lower()
    if 'physics' in s_low:
        return 'Physics'
    if 'chemistry' in s_low:
        return 'Chemistry'
    if 'botany' in s_low or 'plant' in s_low or 'biology' in s_low:
        return 'Botany'
    if 'zoology' in s_low or 'animal' in s_low:
        return 'Zoology'
    if 'math' in s_low or 'algebra' in s_low or 'geometry' in s_low:
        return 'Math'
    return s.strip()


def compute_counters(test_id: int):
    try:
        t = TestSession.objects.get(id=test_id)
    except TestSession.DoesNotExist:
        print(json.dumps({'error': f'TestSession {test_id} not found'}))
        return

    answers = TestAnswer.objects.filter(session_id=t.id).select_related('question__topic')
    subjects = ['Physics', 'Chemistry', 'Botany', 'Zoology', 'Math']
    counters = {s: {'correct': 0, 'incorrect': 0, 'unanswered': 0, 'total_questions': 0} for s in subjects}

    for a in answers:
        topic = getattr(getattr(a, 'question', None), 'topic', None)
        subj_raw = getattr(topic, 'subject', None) if topic else None
        subj = normalize(subj_raw) if subj_raw else None
        if subj not in counters:
            continue
        counters[subj]['total_questions'] += 1
        if a.is_correct is True:
            counters[subj]['correct'] += 1
        elif a.is_correct is False:
            counters[subj]['incorrect'] += 1
        else:
            counters[subj]['unanswered'] += 1

    print(json.dumps({'test_id': test_id, 'counters': counters}, indent=2))


if __name__ == '__main__':
    compute_counters(149)
