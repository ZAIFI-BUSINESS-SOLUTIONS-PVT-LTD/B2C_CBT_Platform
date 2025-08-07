"""
Services Package for NEET App - Simplified Version
Contains essential service modules and components
"""

# Main service classes
from .chatbot_service_refactored import NeetChatbotService

# Essential AI components
from .ai import GeminiClient, SQLAgent

__all__ = [
    'NeetChatbotService',
    'GeminiClient', 
    'SQLAgent'
]
