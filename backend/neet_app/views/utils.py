from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from neomodel import db
from ..models import Topic, Question, TestSession, TestAnswer, StudentProfile
import logging
from django.db import transaction, IntegrityError
import random

logger = logging.getLogger(__name__)


def generate_questions_for_topics(selected_topics, question_count=None):
    """
    Generate questions for the selected topics.
    
    Args:
        selected_topics: List of topic IDs
        question_count: Maximum number of questions to return (optional)
    
    Returns:
        QuerySet of Question objects
    """
    try:
        # Get all questions for the selected topics
        questions = Question.objects.filter(topic_id__in=selected_topics)
        
        # If question_count is specified and we have more questions than needed,
        # randomly select the specified number
        if question_count and questions.count() > question_count:
            # Convert to list, shuffle, and take the first N
            questions_list = list(questions)
            random.shuffle(questions_list)
            # Return a queryset-like structure
            question_ids = [q.id for q in questions_list[:question_count]]
            questions = Question.objects.filter(id__in=question_ids)
        
        logger.info(f"Generated {questions.count()} questions for topics {selected_topics}")
        return questions
        
    except Exception as e:
        logger.error(f"Error generating questions for topics {selected_topics}: {str(e)}")
        # Return empty queryset if there's an error
        return Question.objects.none()



def sync_neo4j_to_postgresql(request):
    """
    Fetches data from Neo4j (Subjects, Chapters, Topics) and
    stores it into the PostgreSQL 'topics' table.
    """
    if request.method != 'GET':
        return JsonResponse({"error": "This endpoint only supports GET requests."}, status=405)

    # Your provided Cypher query
    cypher_query = """
    MATCH (s:Subject)-[:CONTAINS]->(c:Chapter)-[:CONTAINS]->(t:Topic)
    RETURN DISTINCT s.name AS Subject, c.name AS Chapter, t.name AS Topic
    ORDER BY Subject, Chapter, Topic
    """
    
    topics_synced_count = 0
    topics_skipped_count = 0 # Will count skipped duplicates if unique_together is set
    topics_failed_count = 0
    errors = []

    # Define a default icon value since your Neo4j query doesn't return one,
    # and your PostgreSQL 'icon' field is not nullable.
    DEFAULT_ICON = "📚" # You can change this to a more meaningful default like "default_icon.png" or ""

    try:
        # Execute the Cypher query
        results, columns = db.cypher_query(cypher_query)
        
        # Verify the columns returned by the query
        expected_columns = ['Subject', 'Chapter', 'Topic']
        if not all(col in columns for col in expected_columns):
            raise ValueError(
                f"Neo4j query did not return all expected columns. "
                f"Expected: {expected_columns}, Got: {columns}"
            )

        subject_idx = columns.index('Subject')
        chapter_idx = columns.index('Chapter')
        topic_idx = columns.index('Topic')

        # Use a Django database transaction for atomicity when saving to PostgreSQL
        with transaction.atomic():
            for row in results:
                subject_name = row[subject_idx]
                chapter_name = row[chapter_idx]
                topic_name = row[topic_idx]

                try:
                    # Attempt to get an existing topic to avoid duplicates if unique_together is used,
                    # or if you prefer `update_or_create`.
                    # Without `unique_together` on the Topic model, `create` will always insert.
                    
                    # If you have `unique_together = ('subject', 'chapter', 'name')` uncomment this:
                    # topic_obj, created = Topic.objects.get_or_create(
                    #     subject=subject_name,
                    #     chapter=chapter_name,
                    #     name=topic_name,
                    #     defaults={
                    #         'icon': DEFAULT_ICON # Provide icon for new creation
                    #     }
                    # )
                    # if created:
                    #     topics_synced_count += 1
                    # else:
                    #     # If it was already there, you might want to update other fields, or just skip
                    #     # topic_obj.icon = DEFAULT_ICON # Example update
                    #     # topic_obj.save()
                    #     topics_skipped_count += 1
                    #     logger.info(f"Existing topic updated/skipped: {subject_name} - {chapter_name} - {topic_name}")

                    # If you DO NOT have `unique_together`, then every run will create new entries:
                    Topic.objects.create(
                        name=topic_name,
                        subject=subject_name,
                        icon=DEFAULT_ICON, # Using the default icon value
                        chapter=chapter_name if chapter_name is not None else "" # Ensure chapter is not None if TextField expects non-null when not blank/null
                    )
                    topics_synced_count += 1

                except IntegrityError as e:
                    # This block will ONLY be triggered if you have `unique_together`
                    # set on your Topic model and a duplicate is attempted.
                    logger.info(f"Skipping duplicate due to IntegrityError: Subject='{subject_name}', Chapter='{chapter_name}', Topic='{topic_name}' - Error: {e}")
                    topics_skipped_count += 1
                except Exception as e:
                    error_msg = f"Error saving topic '{topic_name}' (Subject: '{subject_name}', Chapter: '{chapter_name}') to PostgreSQL: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    topics_failed_count += 1

    except Exception as e:
        error_msg = f"Overall error fetching data from Neo4j or during transaction: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return JsonResponse({"status": "failed", "message": "An error occurred during synchronization.", "details": errors}, status=500)

    response_data = {
        "status": "success",
        "message": "Neo4j data synchronization to PostgreSQL completed.",
        "topics_synced": topics_synced_count,
        "topics_skipped_duplicates": topics_skipped_count, # Only effective if unique_together is set
        "topics_failed_to_save": topics_failed_count,
        "errors": errors
    }
    return JsonResponse(response_data)



def reset_chapter_structure():
    """
    Resets the chapter structure in Neo4j by clearing all existing nodes and relationships.
    Replicates the functionality from the original views.py reset utility.
    """
    try:
        # Clear all nodes and relationships
        db.cypher_query("MATCH (n) DETACH DELETE n")
        
        return {
            'status': 'success',
            'message': 'Chapter structure reset successfully. All Neo4j nodes and relationships have been cleared.'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error resetting chapter structure: {str(e)}'
        }


def sync_questions_from_neo4j(request=None):
    """
    Syncs questions from Neo4j to PostgreSQL Question model.
    Fetches questions with their options, correct answers, and topics.
    
    IMPORTANT: This function assumes topics are already populated by sync_neo4j_to_postgresql.
    It will NOT create new topics, only reference existing ones.
    """
    try:
        # Cypher query to fetch questions from Neo4j
        cypher_query = """
        MATCH (q:Question)
        RETURN 
          q.question_text AS question_text,
          q.options AS options,
          q.correct_option AS correct_option,
          q.topic_name AS topic_name
        """
        
        # Execute the query
        results, meta = db.cypher_query(cypher_query)
        
        if not results:
            response_data = {
                'status': 'success',
                'message': 'No questions found in Neo4j database.',
                'questions_processed': 0
            }
            if request:
                return JsonResponse(response_data)
            return response_data
        
        questions_created = 0
        errors = []
        topics_not_found = set()  # Track missing topics
        
        for row in results:
            try:
                question_text = row[0]
                options = row[1]  # This should be a list of 4 options
                correct_option = row[2]  # This should be the correct answer
                topic_name = row[3]
                
                # Validate required fields
                if not question_text or not question_text.strip():
                    errors.append(f"Skipping question with empty text")
                    continue
                
                if not topic_name or not topic_name.strip():
                    errors.append(f"Skipping question '{question_text[:50]}...' - no topic name")
                    continue
                
                # Handle options list validation
                if not options or not isinstance(options, list) or len(options) != 4:
                    errors.append(f"Skipping question '{question_text[:50]}...' - invalid options format (expected list of 4)")
                    continue
                
                # Validate all options are non-empty
                if not all(option and option.strip() for option in options):
                    errors.append(f"Skipping question '{question_text[:50]}...' - one or more options are empty")
                    continue
                
                # Extract and normalize correct_option
                if correct_option and isinstance(correct_option, str):
                    # Handle format like "(c) some text" or "(c)"
                    if correct_option.startswith('(') and ')' in correct_option:
                        correct_letter = correct_option[1:correct_option.index(')')].strip().lower()
                    else:
                        correct_letter = correct_option.strip().lower()
                    
                    # Normalize to uppercase A, B, C, D
                    if correct_letter in ['a', '0']:
                        correct_answer = 'A'
                    elif correct_letter in ['b', '1']:
                        correct_answer = 'B'
                    elif correct_letter in ['c', '2']:
                        correct_answer = 'C'
                    elif correct_letter in ['d', '3']:
                        correct_answer = 'D'
                    else:
                        errors.append(f"Skipping question '{question_text[:50]}...' - invalid correct_option: {correct_option}")
                        continue
                else:
                    errors.append(f"Skipping question '{question_text[:50]}...' - missing correct_option")
                    continue
                
                # ✅ FIXED: Only look for existing topics, don't create new ones
                topic = Topic.objects.filter(name=topic_name.strip()).first()
                
                if not topic:
                    # Track missing topics but don't create them
                    topics_not_found.add(topic_name.strip())
                    errors.append(f"Skipping question '{question_text[:50]}...' - topic '{topic_name}' not found in database. Run sync_neo4j_to_postgresql first.")
                    continue
                
                # Clean and prepare question data
                question_text_clean = question_text.strip()
                
                question_data = {
                    'topic': topic,
                    'question': question_text_clean,
                    'option_a': options[0].strip(),
                    'option_b': options[1].strip(),
                    'option_c': options[2].strip(),
                    'option_d': options[3].strip(),
                    'correct_answer': correct_answer,
                    'explanation': 'Explanation not available'  # Default explanation
                }
                
                # Create new question (no duplicate checking as per requirement)
                Question.objects.create(**question_data)
                questions_created += 1
                    
            except Exception as e:
                error_msg = f"Error processing question: {str(e)}"
                errors.append(error_msg)
                continue
        
        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Successfully created {questions_created} questions from Neo4j',
            'questions_created': questions_created,
            'total_processed': questions_created,
            'errors_count': len(errors)
        }
        
        if topics_not_found:
            response_data['missing_topics'] = list(topics_not_found)
            response_data['missing_topics_count'] = len(topics_not_found)
            response_data['recommendation'] = 'Run sync_neo4j_to_postgresql first to populate topics'
        
        if errors:
            response_data['errors'] = errors[:10]  # Limit errors to first 10
            if len(errors) > 10:
                response_data['additional_errors'] = f"... and {len(errors) - 10} more errors"
        
        if request:
            return JsonResponse(response_data)
        return response_data
        
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Failed to sync questions from Neo4j: {str(e)}',
            'questions_processed': 0
        }
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response
