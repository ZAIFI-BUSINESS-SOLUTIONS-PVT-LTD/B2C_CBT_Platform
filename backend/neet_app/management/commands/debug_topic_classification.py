"""
Django management command to debug topic classification issues
"""
from django.core.management.base import BaseCommand
from neet_app.models import Topic, TestSession


class Command(BaseCommand):
    help = 'Debug topic classification for test sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--session-id',
            type=int,
            help='Test session ID to debug (optional)',
        )
        parser.add_argument(
            '--show-topics',
            action='store_true',
            help='Show all topics with their subjects',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Topic Classification Debug Tool'))
        self.stdout.write('=' * 50)

        if options['show_topics']:
            self.show_all_topics()
            return

        session_id = options.get('session_id')
        
        if session_id:
            self.debug_specific_session(session_id)
        else:
            self.debug_latest_sessions()

    def show_all_topics(self):
        """Show all topics grouped by subject"""
        self.stdout.write('\n📚 All Topics by Subject:')
        self.stdout.write('-' * 30)
        
        subjects = Topic.objects.values_list('subject', flat=True).distinct()
        
        for subject in subjects:
            topics = Topic.objects.filter(subject=subject)
            self.stdout.write(f'\n{subject} ({topics.count()} topics):')
            for topic in topics:
                self.stdout.write(f'  • ID: {topic.id} | {topic.name}')

    def debug_specific_session(self, session_id):
        """Debug a specific test session"""
        try:
            session = TestSession.objects.get(id=session_id)
            self.stdout.write(f'\n🎯 Debugging Session ID: {session_id}')
            self.stdout.write('-' * 30)
            
            self.stdout.write(f'Selected Topics: {session.selected_topics}')
            self.stdout.write(f'Physics Topics: {session.physics_topics}')
            self.stdout.write(f'Chemistry Topics: {session.chemistry_topics}')
            self.stdout.write(f'Botany Topics: {session.botany_topics}')
            self.stdout.write(f'Zoology Topics: {session.zoology_topics}')
            
            # Get the actual topic objects
            self.stdout.write('\n📝 Topic Details:')
            if session.selected_topics:
                topics = Topic.objects.filter(id__in=session.selected_topics)
                for topic in topics:
                    self.stdout.write(f'  • ID: {topic.id} | Subject: {topic.subject} | Name: {topic.name}')
            
            # Re-run classification
            self.stdout.write('\n🔄 Re-running classification...')
            session.update_subject_classification()
            session.refresh_from_db()
            
            self.stdout.write('After re-classification:')
            self.stdout.write(f'Physics Topics: {session.physics_topics}')
            self.stdout.write(f'Chemistry Topics: {session.chemistry_topics}')
            self.stdout.write(f'Botany Topics: {session.botany_topics}')
            self.stdout.write(f'Zoology Topics: {session.zoology_topics}')
            
        except TestSession.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Session {session_id} not found'))

    def debug_latest_sessions(self):
        """Debug the latest 5 test sessions"""
        self.stdout.write('\n📊 Latest 5 Test Sessions:')
        self.stdout.write('-' * 30)
        
        sessions = TestSession.objects.order_by('-id')[:5]
        
        for session in sessions:
            self.stdout.write(f'\nSession ID: {session.id}')
            self.stdout.write(f'  Selected Topics: {session.selected_topics}')
            self.stdout.write(f'  Physics: {len(session.physics_topics)} topics')
            self.stdout.write(f'  Chemistry: {len(session.chemistry_topics)} topics')
            self.stdout.write(f'  Botany: {len(session.botany_topics)} topics')
            self.stdout.write(f'  Zoology: {len(session.zoology_topics)} topics')
            
            # Show which topics are selected
            if session.selected_topics:
                topics = Topic.objects.filter(id__in=session.selected_topics)
                subject_count = {}
                for topic in topics:
                    subject_count[topic.subject] = subject_count.get(topic.subject, 0) + 1
                
                self.stdout.write(f'  Actual subject distribution: {subject_count}')
