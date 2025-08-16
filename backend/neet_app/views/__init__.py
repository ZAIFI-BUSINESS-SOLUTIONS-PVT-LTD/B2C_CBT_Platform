# Import all views to make them available when importing from neet_app.views
from .topic_views import TopicViewSet, initialize_chapter_structure
from .question_views import QuestionViewSet
from .test_session_views import TestSessionViewSet
from .test_answer_views import TestAnswerViewSet
from .student_profile_views import StudentProfileViewSet
from .review_comment_views import ReviewCommentViewSet
from .dashboard_views import dashboard_analytics, dashboard_comprehensive_analytics
from .time_tracking_views import TimeTrackingViewSet
from .chatbot_views import ChatSessionViewSet, chat_statistics
from .insights_views import get_student_insights, get_topic_details, get_insights_config
from .utils import sync_all_from_database_question,sync_topics_from_database_question,sync_all_from_database_question, reset_questions_and_topics
# Make all views available for import
__all__ = [
    'TopicViewSet',
    'QuestionViewSet', 
    'TestSessionViewSet',
    'TestAnswerViewSet',
    'StudentProfileViewSet',
    'ReviewCommentViewSet',
    'TimeTrackingViewSet',
    'ChatSessionViewSet',
    'dashboard_analytics',
    'dashboard_comprehensive_analytics',
    'chat_statistics',
    'get_student_insights',
    'get_topic_details', 
    'get_insights_config',
    'initialize_chapter_structure',
    'reset_chapter_structure',
    'sync_topics_from_database_question',
    'sync_questions_from_database_question',
    'sync_all_from_database_question',
    'reset_questions_and_topics'
]
