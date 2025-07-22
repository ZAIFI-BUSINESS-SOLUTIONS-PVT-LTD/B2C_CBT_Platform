from django.core.management.base import BaseCommand
from neet_app.models import Topic, Question
import random

class Command(BaseCommand):
    help = 'Populate the database with NEET topics and questions'

    def handle(self, *args, **options):
        # Check if data already exists
        if Topic.objects.exists():
            self.stdout.write(self.style.WARNING('Data already exists. Skipping...'))
            return

        # Create Physics topics
        physics_topics = [
            {'name': 'Kinematics', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Dynamics', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Work, Energy and Power', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Rotational Motion', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Gravitation', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Properties of Matter', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Thermodynamics', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Kinetic Theory', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Oscillations', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Waves', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Electrostatics', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Current Electricity', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Electromagnetic Induction', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Optics', 'subject': 'Physics', 'icon': '⚡'},
            {'name': 'Modern Physics', 'subject': 'Physics', 'icon': '⚡'},
        ]

        # Create Chemistry topics
        chemistry_topics = [
            {'name': 'Some Basic Concepts of Chemistry', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Structure of Atom', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Classification of Elements', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Chemical Bonding', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'States of Matter', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Thermodynamics', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Equilibrium', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Redox Reactions', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Hydrogen', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'The s-Block Elements', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'The p-Block Elements', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Organic Chemistry', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Hydrocarbons', 'subject': 'Chemistry', 'icon': '🧪'},
            {'name': 'Environmental Chemistry', 'subject': 'Chemistry', 'icon': '🧪'},
        ]

        # Create Biology topics
        biology_topics = [
            {'name': 'The Living World', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Biological Classification', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Plant Kingdom', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Animal Kingdom', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Morphology of Flowering Plants', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Anatomy of Flowering Plants', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Structural Organisation in Animals', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Cell: The Unit of Life', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Biomolecules', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Cell Cycle and Cell Division', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Photosynthesis', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Respiration in Plants', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Plant Growth and Development', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Digestion and Absorption', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Breathing and Exchange of Gases', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Body Fluids and Circulation', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Excretory Products and Elimination', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Locomotion and Movement', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Neural Control and Coordination', 'subject': 'Biology', 'icon': '🧬'},
            {'name': 'Chemical Coordination', 'subject': 'Biology', 'icon': '🧬'},
        ]

        # Create all topics
        all_topics = physics_topics + chemistry_topics + biology_topics
        created_topics = []
        
        for topic_data in all_topics:
            topic = Topic.objects.create(**topic_data)
            created_topics.append(topic)
            self.stdout.write(f'Created topic: {topic.subject} - {topic.name}')

        # Create sample questions for each topic
        for topic in created_topics:
            num_questions = random.randint(8, 15)  # Random number of questions per topic
            
            for i in range(num_questions):
                question = self.generate_question(topic, i + 1)
                Question.objects.create(**question)
            
            self.stdout.write(f'Created {num_questions} questions for {topic.name}')

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {len(created_topics)} topics with questions'))

    def generate_question(self, topic, question_num):
        """Generate a sample question for a given topic"""
        if topic.subject == 'Physics':
            return self.generate_physics_question(topic, question_num)
        elif topic.subject == 'Chemistry':
            return self.generate_chemistry_question(topic, question_num)
        else:  # Biology
            return self.generate_biology_question(topic, question_num)

    def generate_physics_question(self, topic, question_num):
        questions = {
            'Kinematics': [
                {
                    'question': 'A particle moves in a straight line with constant acceleration. If it covers 20 m in the first 2 seconds and 60 m in the next 4 seconds, what is its acceleration?',
                    'option_a': '5 m/s²',
                    'option_b': '10 m/s²',
                    'option_c': '15 m/s²',
                    'option_d': '20 m/s²',
                    'correct_answer': 'A',
                    'explanation': 'Using kinematic equations: s = ut + ½at². From given data, acceleration = 5 m/s².'
                },
                {
                    'question': 'A ball is thrown vertically upward with initial velocity 20 m/s. What is the maximum height reached? (g = 10 m/s²)',
                    'option_a': '10 m',
                    'option_b': '20 m',
                    'option_c': '30 m',
                    'option_d': '40 m',
                    'correct_answer': 'B',
                    'explanation': 'Using v² = u² + 2as, at maximum height v = 0, so h = u²/2g = 400/20 = 20 m.'
                }
            ],
            'Electrostatics': [
                {
                    'question': 'Two point charges of +2μC and -3μC are separated by 10 cm. The force between them is:',
                    'option_a': 'Attractive',
                    'option_b': 'Repulsive',
                    'option_c': 'Zero',
                    'option_d': 'Cannot be determined',
                    'correct_answer': 'A',
                    'explanation': 'Unlike charges attract each other, so the force is attractive.'
                }
            ]
        }
        
        topic_questions = questions.get(topic.name, [])
        if topic_questions and question_num <= len(topic_questions):
            return {
                'topic': topic,
                **topic_questions[question_num - 1]
            }
        
        # Generic physics question
        return {
            'topic': topic,
            'question': f'Sample {topic.name} question {question_num}: What is the fundamental principle?',
            'option_a': 'Option A',
            'option_b': 'Option B',
            'option_c': 'Option C',
            'option_d': 'Option D',
            'correct_answer': random.choice(['A', 'B', 'C', 'D']),
            'explanation': f'This is a sample explanation for {topic.name} question {question_num}.'
        }

    def generate_chemistry_question(self, topic, question_num):
        questions = {
            'Structure of Atom': [
                {
                    'question': 'The maximum number of electrons in a subshell with l = 2 is:',
                    'option_a': '2',
                    'option_b': '6',
                    'option_c': '10',
                    'option_d': '14',
                    'correct_answer': 'C',
                    'explanation': 'For l = 2 (d subshell), maximum electrons = 2(2l + 1) = 2(5) = 10.'
                }
            ],
            'Chemical Bonding': [
                {
                    'question': 'The shape of NH₃ molecule is:',
                    'option_a': 'Tetrahedral',
                    'option_b': 'Trigonal pyramidal',
                    'option_c': 'Trigonal planar',
                    'option_d': 'Linear',
                    'correct_answer': 'B',
                    'explanation': 'NH₃ has tetrahedral electron geometry but trigonal pyramidal molecular geometry due to lone pair.'
                }
            ]
        }
        
        topic_questions = questions.get(topic.name, [])
        if topic_questions and question_num <= len(topic_questions):
            return {
                'topic': topic,
                **topic_questions[question_num - 1]
            }
        
        # Generic chemistry question
        return {
            'topic': topic,
            'question': f'Sample {topic.name} question {question_num}: What is the chemical principle?',
            'option_a': 'Option A',
            'option_b': 'Option B',
            'option_c': 'Option C',
            'option_d': 'Option D',
            'correct_answer': random.choice(['A', 'B', 'C', 'D']),
            'explanation': f'This is a sample explanation for {topic.name} question {question_num}.'
        }

    def generate_biology_question(self, topic, question_num):
        questions = {
            'Cell: The Unit of Life': [
                {
                    'question': 'The powerhouse of the cell is:',
                    'option_a': 'Nucleus',
                    'option_b': 'Mitochondria',
                    'option_c': 'Ribosome',
                    'option_d': 'Endoplasmic reticulum',
                    'correct_answer': 'B',
                    'explanation': 'Mitochondria are called the powerhouse of the cell because they produce ATP through cellular respiration.'
                }
            ],
            'Photosynthesis': [
                {
                    'question': 'The raw materials for photosynthesis are:',
                    'option_a': 'CO₂ and H₂O',
                    'option_b': 'O₂ and H₂O',
                    'option_c': 'CO₂ and O₂',
                    'option_d': 'Glucose and O₂',
                    'correct_answer': 'A',
                    'explanation': 'Photosynthesis uses CO₂ and H₂O in the presence of sunlight to produce glucose and oxygen.'
                }
            ]
        }
        
        topic_questions = questions.get(topic.name, [])
        if topic_questions and question_num <= len(topic_questions):
            return {
                'topic': topic,
                **topic_questions[question_num - 1]
            }
        
        # Generic biology question
        return {
            'topic': topic,
            'question': f'Sample {topic.name} question {question_num}: What is the biological concept?',
            'option_a': 'Option A',
            'option_b': 'Option B',
            'option_c': 'Option C',
            'option_d': 'Option D',
            'correct_answer': random.choice(['A', 'B', 'C', 'D']),
            'explanation': f'This is a sample explanation for {topic.name} question {question_num}.'
        }