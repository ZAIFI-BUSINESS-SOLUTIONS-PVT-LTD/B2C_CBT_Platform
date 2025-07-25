"""
Management command to test the new authentication system and create sample students
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from neet_app.models import StudentProfile, TestSession, Topic
from neet_app.utils.topic_utils import classify_topics_by_subject


class Command(BaseCommand):
    help = 'Test new authentication system and create sample students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-students',
            action='store_true',
            help='Create sample students',
        )
        parser.add_argument(
            '--test-authentication',
            action='store_true',
            help='Test student authentication',
        )
        parser.add_argument(
            '--classify-topics',
            action='store_true',
            help='Test topic classification',
        )

    def handle(self, *args, **options):
        if options['create_students']:
            self.create_sample_students()
        
        if options['test_authentication']:
            self.test_authentication()
        
        if options['classify_topics']:
            self.test_topic_classification()

    def create_sample_students(self):
        """Create sample students with auto-generated credentials"""
        self.stdout.write("Creating sample students...")
        
        sample_students = [
            {
                'full_name': 'Ramesh Kumar',
                'email': 'ramesh.kumar@example.com',
                'phone_number': '+91-9876543210',
                'date_of_birth': date(2005, 7, 8),
                'school_name': 'Delhi Public School',
                'target_exam_year': 2025,
                'grade_class': '12th',
                'preferred_subjects': ['Physics', 'Chemistry', 'Botany']
            },
            {
                'full_name': 'Priya Sharma',
                'email': 'priya.sharma@example.com',
                'phone_number': '+91-9876543211',
                'date_of_birth': date(2005, 12, 15),
                'school_name': 'Modern School',
                'target_exam_year': 2025,
                'grade_class': '12th',
                'preferred_subjects': ['Chemistry', 'Botany', 'Zoology']
            },
            {
                'full_name': 'Arjun Patel',
                'email': 'arjun.patel@example.com',
                'phone_number': '+91-9876543212',
                'date_of_birth': date(2004, 3, 22),
                'school_name': 'Kendriya Vidyalaya',
                'target_exam_year': 2025,
                'grade_class': 'Dropper',
                'preferred_subjects': ['Physics', 'Chemistry', 'Zoology']
            }
        ]
        
        created_students = []
        
        for student_data in sample_students:
            # Check if student already exists
            if StudentProfile.objects.filter(email=student_data['email']).exists():
                self.stdout.write(
                    self.style.WARNING(f"Student with email {student_data['email']} already exists")
                )
                continue
            
            try:
                student = StudentProfile.objects.create(**student_data)
                created_students.append(student)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created student: {student.full_name}\n"
                        f"  Student ID: {student.student_id}\n"
                        f"  Generated Password: {student.generated_password}\n"
                        f"  Email: {student.email}\n"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating student {student_data['full_name']}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {len(created_students)} students")
        )

    def test_authentication(self):
        """Test student authentication functionality"""
        self.stdout.write("Testing authentication system...")
        
        # Get first student
        student = StudentProfile.objects.first()
        if not student:
            self.stdout.write(self.style.ERROR("No students found. Create students first."))
            return
        
        # Test password verification
        if student.generated_password:
            if student.check_password(student.generated_password):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Password verification successful for {student.student_id}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Password verification failed for {student.student_id}"
                    )
                )
        
        # Test wrong password
        if not student.check_password("wrongpassword"):
            self.stdout.write(
                self.style.SUCCESS("✓ Wrong password correctly rejected")
            )
        else:
            self.stdout.write(
                self.style.ERROR("✗ Wrong password was accepted")
            )

    def test_topic_classification(self):
        """Test topic classification functionality"""
        self.stdout.write("Testing topic classification...")
        
        classification = classify_topics_by_subject()
        
        total_topics = sum(len(topics) for topics in classification.values())
        
        self.stdout.write(f"Total topics classified: {total_topics}")
        
        for subject, topics in classification.items():
            self.stdout.write(f"{subject}: {len(topics)} topics")
            
            # Show first few topics as examples
            if topics:
                examples = topics[:3]
                self.stdout.write(f"  Examples: {', '.join(examples)}")
        
        # Test creating a test session with topic classification
        self.test_session_creation()

    def test_session_creation(self):
        """Test creating a test session with topic classification"""
        self.stdout.write("Testing test session creation...")
        
        # Get a student
        student = StudentProfile.objects.first()
        if not student:
            self.stdout.write(self.style.ERROR("No students found for session creation test"))
            return
        
        # Get some topic IDs
        topics = Topic.objects.all()[:5]
        if not topics:
            self.stdout.write(self.style.ERROR("No topics found for session creation test"))
            return
        
        selected_topic_ids = [str(topic.id) for topic in topics]
        
        try:
            # Create test session
            session = TestSession.objects.create(
                student_id=student.student_id,
                selected_topics=selected_topic_ids,
                time_limit=60,  # 60 minutes
                question_count=10,
                start_time=timezone.now(),
                total_questions=10
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Test session created successfully\n"
                    f"  Session ID: {session.id}\n"
                    f"  Student: {session.student_id}\n"
                    f"  Selected topics: {len(session.selected_topics)} topics\n"
                    f"  Physics topics: {len(session.physics_topics)}\n"
                    f"  Chemistry topics: {len(session.chemistry_topics)}\n"
                    f"  Botany topics: {len(session.botany_topics)}\n"
                    f"  Zoology topics: {len(session.zoology_topics)}\n"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error creating test session: {str(e)}")
            )
