from django.core.management.base import BaseCommand
import json
import random

from neet_app.models import Question
from neet_app.views.utils import generate_questions_for_topics


def _normalize_label(val):
    if not val:
        return 'unknown'
    s = str(val).strip().lower()
    if s in ('easy', 'e', '1', 'beginner', 'low'):
        return 'easy'
    if s in ('medium', 'med', 'm', '2', 'intermediate'):
        return 'medium'
    if s in ('hard', 'h', '3', 'advanced', 'high'):
        return 'hard'
    if s.isdigit():
        if s == '1':
            return 'easy'
        if s == '2':
            return 'medium'
        if s == '3':
            return 'hard'
    if 'easy' in s:
        return 'easy'
    if 'medium' in s or 'intermediate' in s:
        return 'medium'
    if 'hard' in s or 'advanced' in s:
        return 'hard'
    return 'unknown'


class Command(BaseCommand):
    help = 'Diagnose question availability and selection by difficulty for given topic ids'

    def add_arguments(self, parser):
        parser.add_argument('--topic-ids', '-t', type=str, required=True,
                            help='Comma-separated list of topic IDs, e.g. 1,2,3')
        parser.add_argument('--count', '-c', type=int, required=True,
                            help='Number of questions to select for the session')
        parser.add_argument('--dist', '-d', type=str, required=False,
                            help='Difficulty distribution as "easy,medium,hard" counts (e.g. "4,3,3") or JSON like "{\"easy\":4,\"medium\":3,\"hard\":3}"')

    def handle(self, *args, **options):
        topic_ids = [int(x) for x in options['topic_ids'].split(',') if x.strip()]
        question_count = options['count']
        dist_raw = options.get('dist')

        distribution = None
        if dist_raw:
            dist_raw = dist_raw.strip()
            if dist_raw.startswith('{'):
                try:
                    distribution = json.loads(dist_raw)
                except Exception as e:
                    self.stderr.write(f'Failed to parse JSON distribution: {e}')
                    return
            else:
                parts = [p.strip() for p in dist_raw.split(',') if p.strip()]
                if len(parts) == 3:
                    try:
                        distribution = {'easy': int(parts[0]), 'medium': int(parts[1]), 'hard': int(parts[2])}
                    except Exception as e:
                        self.stderr.write(f'Failed to parse comma distribution: {e}')
                        return

        self.stdout.write(f'Inspecting topics: {topic_ids}  target_count={question_count}  distribution={distribution}')

        qs = Question.objects.filter(topic_id__in=topic_ids)
        total = qs.count()
        self.stdout.write(f'Total questions in these topics: {total}')

        # distinct raw difficulty values
        raw_vals = qs.values_list('difficulty', flat=True)
        raw_counts = {}
        for v in raw_vals:
            raw_counts[v] = raw_counts.get(v, 0) + 1

        self.stdout.write('\nDistinct raw difficulty values and counts:')
        for k, v in sorted(raw_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {repr(k)}: {v}')

        # normalized buckets
        buckets = {'easy': [], 'medium': [], 'hard': [], 'unknown': []}
        for q in qs:
            label = _normalize_label(q.difficulty)
            buckets[label].append(q)

        self.stdout.write('\nNormalized bucket sizes:')
        for k in ('easy', 'medium', 'hard', 'unknown'):
            self.stdout.write(f'  {k}: {len(buckets[k])}')

        # Show sample ids from each bucket (up to 10)
        for k in ('easy', 'medium', 'hard', 'unknown'):
            sample = [q.id for q in buckets[k][:10]]
            self.stdout.write(f'  sample {k} ids: {sample}')

        # Now call the generator to see what it would pick
        self.stdout.write('\nRunning generator to select questions...')
        selected_qs = generate_questions_for_topics(topic_ids, question_count, exclude_question_ids=None, difficulty_distribution=distribution)

        sel_list = list(selected_qs)
        self.stdout.write(f'Selected {len(sel_list)} questions (requested {question_count})')

        # breakdown of selected by normalized difficulty
        sel_buckets = {'easy': [], 'medium': [], 'hard': [], 'unknown': []}
        for q in sel_list:
            sel_buckets[_normalize_label(q.difficulty)].append(q)

        self.stdout.write('\nSelected breakdown:')
        for k in ('easy', 'medium', 'hard', 'unknown'):
            self.stdout.write(f'  {k}: {len(sel_buckets[k])}  ids: {[q.id for q in sel_buckets[k]]}')

        self.stdout.write('\nFull selected list (id, difficulty, topic_id):')
        for q in sel_list:
            self.stdout.write(f'  {q.id}  {q.difficulty!r}  topic={q.topic_id}')

        self.stdout.write('\nDone.')
