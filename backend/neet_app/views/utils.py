from django.http import JsonResponse
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from neomodel import db
from ..models import Topic, Question, TestSession, TestAnswer, StudentProfile
import logging

logger = logging.getLogger(__name__)


def _extract_subject_from_topic(topic_name):
    """Extract subject from topic name using keywords"""
    topic_lower = topic_name.lower()
    
    if any(keyword in topic_lower for keyword in ['physics', 'mechanics', 'thermodynamics', 'electromagnetism', 'optics', 'modern physics']):
        return 'Physics'
    elif any(keyword in topic_lower for keyword in ['chemistry', 'organic', 'inorganic', 'physical chemistry', 'chemical']):
        return 'Chemistry'
    elif any(keyword in topic_lower for keyword in ['botany', 'plant', 'photosynthesis', 'respiration', 'morphology']):
        return 'Botany'
    elif any(keyword in topic_lower for keyword in ['zoology', 'animal', 'human', 'anatomy', 'physiology', 'evolution']):
        return 'Zoology'
    else:
        return 'General'


def _extract_chapter_from_topic(topic_name):
    """Extract chapter from topic name - use the topic name as chapter"""
    return topic_name if topic_name else 'General'


def sync_neo4j_to_postgresql(request=None):
    """
    Synchronizes data from Neo4j to PostgreSQL database.
    Replicates the functionality from the original views.py sync utility.
    """
    try:
        query = """
        MATCH (t:Topic)-[:HAS_QUESTION]->(q:Question)
        RETURN t.id AS topic_id, t.subject AS subject, t.chapter AS chapter, t.name AS topic_name,
               q.id AS question_id, q.content AS question_content, q.correct_answer AS correct_answer,
               q.option_a AS option_a, q.option_b AS option_b, q.option_c AS option_c, q.option_d AS option_d
        """
        results, meta = db.cypher_query(query)

        synced_topics = set()
        synced_questions = 0

        for row in results:
            topic_id = row[0]
            subject = row[1]
            chapter = row[2]
            topic_name = row[3]
            question_id = row[4]
            question_content = row[5]
            correct_answer = row[6]
            option_a = row[7]
            option_b = row[8]
            option_c = row[9]
            option_d = row[10]

            # Create or update topic
            topic, created = Topic.objects.get_or_create(
                id=topic_id,
                defaults={
                    'subject': subject,
                    'chapter': chapter,
                    'name': topic_name
                }
            )

            if created:
                synced_topics.add(topic_id)

            # Create or update question
            question, created = Question.objects.get_or_create(
                id=question_id,
                defaults={
                    'topic': topic,
                    'content': question_content,
                    'correct_answer': correct_answer,
                    'option_a': option_a,
                    'option_b': option_b,
                    'option_c': option_c,
                    'option_d': option_d
                }
            )

            if created:
                synced_questions += 1

        response_data = {
            'status': 'success',
            'synced_topics': len(synced_topics),
            'synced_questions': synced_questions,
            'message': f'Successfully synced {len(synced_topics)} topics and {synced_questions} questions from Neo4j to PostgreSQL'
        }

        if request:
            return JsonResponse(response_data)
        return response_data

    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Error syncing data: {str(e)}'
        }
        
        if request:
            return JsonResponse(error_response, status=500)
        return error_response


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
        topics_created = 0
        
        for row in results:
            try:
                question_text = row[0]
                options = row[1]  # This should be a list of 4 options
                correct_option = row[2]  # This should be the correct answer
                topic_name = row[3]
                
                # Validate required fields
                if not question_text or not isinstance(question_text, str):
                    errors.append(f"Skipping question with invalid/empty question text")
                    continue
                
                if not topic_name or not isinstance(topic_name, str):
                    errors.append(f"Skipping question '{question_text[:50]}...' - invalid/empty topic name")
                    continue
                
                # Handle options list - ensure it's exactly 4 non-empty strings
                if not options or not isinstance(options, list):
                    errors.append(f"Skipping question '{question_text[:50]}...' - options is not a list")
                    continue
                    
                if len(options) != 4:
                    errors.append(f"Skipping question '{question_text[:50]}...' - expected 4 options, got {len(options)}")
                    continue
                
                # Validate all options are non-empty strings
                valid_options = []
                for i, option in enumerate(options):
                    if not option or not isinstance(option, str):
                        errors.append(f"Skipping question '{question_text[:50]}...' - option {i+1} is invalid")
                        break
                    valid_options.append(option.strip())
                
                if len(valid_options) != 4:
                    continue
                
                # Extract and normalize correct_option
                # Handle formats like "(c) limbic system", "(a)", "c", "C", "2", etc.
                correct_answer = None
                
                if isinstance(correct_option, str):
                    # Clean the correct_option string
                    clean_option = correct_option.strip().lower()
                    
                    # Extract letter from patterns like "(c)" or "(c) some text"
                    if clean_option.startswith('(') and ')' in clean_option:
                        # Extract letter between parentheses
                        letter_part = clean_option.split(')')[0].replace('(', '').strip()
                    else:
                        letter_part = clean_option
                    
                    # Normalize to A, B, C, D
                    if letter_part in ['a', '0']:
                        correct_answer = 'A'
                    elif letter_part in ['b', '1']:
                        correct_answer = 'B'
                    elif letter_part in ['c', '2']:
                        correct_answer = 'C'
                    elif letter_part in ['d', '3']:
                        correct_answer = 'D'
                    elif letter_part.upper() in ['A', 'B', 'C', 'D']:
                        correct_answer = letter_part.upper()
                
                # Validate that we got a valid answer
                if correct_answer not in ['A', 'B', 'C', 'D']:
                    errors.append(f"Skipping question '{question_text[:50]}...' - could not parse correct_option: {correct_option}")
                    continue
                
                # Get or create topic - use first match if duplicates exist
                topic = Topic.objects.filter(name=topic_name).first()
                
                if not topic:
                    # Create new topic if none exists
                    topic = Topic.objects.create(
                        name=topic_name,
                        chapter=_extract_chapter_from_topic(topic_name),
                        subject=_extract_subject_from_topic(topic_name)
                    )
                    topics_created += 1
                
                # Always create new question - don't check for duplicates
                # This allows multiple questions per topic and handles any duplicates from Neo4j
                question_data = {
                    'topic': topic,
                    'question': question_text.strip(),
                    'option_a': valid_options[0],
                    'option_b': valid_options[1],
                    'option_c': valid_options[2],
                    'option_d': valid_options[3],
                    'correct_answer': correct_answer,
                    'explanation': 'Explanation not available'
                }
                
                try:
                    Question.objects.create(**question_data)
                    questions_created += 1
                except Exception as create_error:
                    errors.append(f"Failed to create question '{question_text[:50]}...': {str(create_error)}")
                    continue
                    
            except Exception as e:
                error_msg = f"Error processing question: {str(e)}"
                errors.append(error_msg)
                continue
        
        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'Successfully created {questions_created} questions from Neo4j',
            'questions_created': questions_created,
            'topics_created': topics_created,
            'total_processed': questions_created,
            'errors_count': len(errors)
        }
        
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
