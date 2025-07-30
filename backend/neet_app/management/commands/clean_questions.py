"""
Management command to clean mathematical expressions in existing questions
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from neet_app.models import Question
from neet_app.views.utils import clean_mathematical_text
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean mathematical expressions in existing questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of questions to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without making changes'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Find questions that likely contain LaTeX/regex patterns
        patterns = ['\\\\', '$', '^{', '_{', '\\frac', '\\sqrt', '\\alpha', '\\beta']
        questions_to_clean = Question.objects.filter(
            question__iregex=r'\\\\|\\$|\\^\\{|_\\{|\\\\frac|\\\\sqrt|\\\\alpha|\\\\beta'
        )
        
        total_questions = questions_to_clean.count()
        self.stdout.write(f'Found {total_questions} questions that may need cleaning')
        
        if total_questions == 0:
            self.stdout.write(
                self.style.SUCCESS('No questions found that need cleaning')
            )
            return
        
        processed = 0
        cleaned = 0
        
        for i in range(0, total_questions, batch_size):
            batch = questions_to_clean[i:i + batch_size]
            
            with transaction.atomic():
                for question in batch:
                    original_question = question.question
                    original_options = [
                        question.option_a, question.option_b, 
                        question.option_c, question.option_d
                    ]
                    
                    # Clean the text
                    cleaned_question = clean_mathematical_text(question.question)
                    cleaned_options = [
                        clean_mathematical_text(question.option_a),
                        clean_mathematical_text(question.option_b),
                        clean_mathematical_text(question.option_c),
                        clean_mathematical_text(question.option_d)
                    ]
                    
                    # Check if any changes were made
                    changes_made = (
                        original_question != cleaned_question or
                        original_options != cleaned_options
                    )
                    
                    if changes_made:
                        if dry_run:
                            self.stdout.write(f'Would clean question ID {question.id}:')
                            self.stdout.write(f'  Original: {original_question[:100]}...')
                            self.stdout.write(f'  Cleaned:  {cleaned_question[:100]}...')
                        else:
                            question.question = cleaned_question
                            question.option_a = cleaned_options[0]
                            question.option_b = cleaned_options[1]
                            question.option_c = cleaned_options[2]
                            question.option_d = cleaned_options[3]
                            question.save(update_fields=[
                                'question', 'option_a', 'option_b', 'option_c', 'option_d'
                            ])
                        
                        cleaned += 1
                    
                    processed += 1
            
            # Progress update
            self.stdout.write(f'Processed {processed}/{total_questions} questions...')
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE: {cleaned} questions would be cleaned out of {processed} processed'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleaned {cleaned} questions out of {processed} processed'
                )
            )
