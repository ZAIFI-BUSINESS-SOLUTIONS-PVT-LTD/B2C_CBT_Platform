"""Check test 149 data and zone insights"""
from neet_app.models import TestSession, TestAnswer, TestSubjectZoneInsight

test = TestSession.objects.get(id=149)

print('=' * 60)
print('TEST 149 DATA')
print('=' * 60)
print(f'Test name: Practice Test #{test.id}')
print(f'Start time: {test.start_time}')
print(f'End time: {test.end_time}')
print(f'Correct: {test.correct_answers}')
print(f'Incorrect: {test.incorrect_answers}')
print(f'Total marks: {(test.correct_answers * 4) - (test.incorrect_answers * 1)}')
print(f'Max marks: {test.total_questions * 4}')

print(f'\n{"=" * 60}')
print('ZONE INSIGHTS IN DATABASE')
print('=' * 60)
zones = TestSubjectZoneInsight.objects.filter(test_session_id=149)
print(f'Count: {zones.count()}\n')

for z in zones:
    print(f'Subject: {z.subject}')
    # Backwards-compatible access to renamed fields
    print(f'  Checkpoints: {getattr(z, "checkpoints", [])}')
    print(f'  Topics analyzed: {getattr(z, "topics_analyzed", [])}')
    # New structured fields (if present)
    print(f'  Subject data: {getattr(z, "subject_data", None)}')
    print(f'  Time spent: {getattr(z, "time_spend", None)}')
    print()

if zones.count() == 0:
    print('⚠️ NO ZONE INSIGHTS FOUND - Need to generate them!')
    print(f'\nTest has these subjects with topics:')
    print(f'  Physics: {test.physics_topics}')
    print(f'  Chemistry: {test.chemistry_topics}')
    print(f'  Botany: {test.botany_topics}')
    print(f'  Zoology: {test.zoology_topics}')
