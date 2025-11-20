"""
Password validation utilities for user-defined passwords
Implements industry-standard password policies and validation
"""
import re
from typing import Dict, List, Tuple


# Common weak passwords blocklist
COMMON_PASSWORDS = {
    'password', 'password123', '123456', '123456789', 'qwerty', 'abc123',
    'password1', 'admin', 'root', 'user', 'test', 'guest', 'demo',
    '111111', '000000', '123123', 'welcome', 'login', 'master',
    'passw0rd', 'p@ssword', 'p@ssw0rd', 'letmein', 'changeme',
    'neet2024', 'neet2025', 'student', 'student123'
}


def validate_password_strength(password: str) -> Tuple[bool, List[str], int]:
    """
    Validate password strength according to industry standards
    
    Args:
        password (str): Password to validate
        
    Returns:
        Tuple[bool, List[str], int]: (is_valid, error_messages, strength_score)
        strength_score: 0-100 (0=weak, 100=very strong)
    """
    errors = []
    strength_score = 0

    # New relaxed policy: only enforce minimum length of 6 characters
    # Keep maximum length as 64 to be compatible with storage limits
    if len(password) < 6:
        errors.append("Password must be at least 6 characters long")
    else:
        # minimal positive score for satisfying length
        strength_score = 50

    if len(password) > 64:
        errors.append("Password must be no more than 64 characters long")
        return False, errors, 0

    is_valid = len(errors) == 0
    return is_valid, errors, strength_score


def get_password_strength_label(score: int) -> str:
    """
    Get human-readable password strength label
    
    Args:
        score (int): Strength score (0-100)
        
    Returns:
        str: Strength label
    """
    if score < 30:
        return "Very Weak"
    elif score < 50:
        return "Weak"
    elif score < 70:
        return "Fair"
    elif score < 85:
        return "Good"
    else:
        return "Strong"


def validate_password_confirmation(password: str, password_confirmation: str) -> Tuple[bool, str]:
    """
    Validate password confirmation matches
    
    Args:
        password (str): Original password
        password_confirmation (str): Confirmation password
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if password != password_confirmation:
        return False, "Passwords do not match"
    return True, ""


def validate_full_name_uniqueness(full_name: str, email: str = None, exclude_student_id: str = None) -> Tuple[bool, str]:
    """
    Validate uniqueness of the (full_name, email) combination.

    Historically the code enforced full_name as globally unique which caused
    collisions when different students share the same name. Change the policy
    to allow duplicate full names as long as the email differs. If `email` is
    provided this will check for an existing record with the same name and
    email. If `email` is not provided it will only check for the presence of
    any users with that full_name and return a helpful message advising the
    frontend to also check availability by email.

    Args:
        full_name: Full name to check (case-insensitive)
        email: Optional email to pair with the name when testing uniqueness
        exclude_student_id: Optional student_id to exclude (for updates)

    Returns:
        Tuple[bool, str]: (is_unique, error_message)
    """
    from ..models import StudentProfile

    # Base queryset for the full_name (case-insensitive)
    query = StudentProfile.objects.filter(full_name__iexact=full_name)
    if exclude_student_id:
        query = query.exclude(student_id=exclude_student_id)

    if email:
        # If email provided, check for existing record with same full_name and email
        exists = query.filter(email__iexact=email).exists()
        if exists:
            return False, "A user with this name and email already exists. Please use different credentials or login."
        # If no exact match, name+email combination is available
        return True, ""

    # No email provided: inform the caller that name alone is not a reliable uniqueness check
    if query.exists():
        return False, "This name is already used by another user. Provide an email to check full availability or choose a distinguishing name."

    return True, ""


def generate_password_suggestions(base_name: str = None) -> List[str]:
    """
    Generate secure password suggestions for users
    
    Args:
        base_name (str): Optional base name for personalized suggestions
        
    Returns:
        List[str]: List of suggested passwords
    """
    import random
    import string
    
    suggestions = []
    
    # Pattern-based suggestions
    patterns = [
        "Neet@{year}{num}",
        "Study{word}#{num}",
        "Exam{word}{year}!",
        "Success{num}@{word}"
    ]
    
    words = ["Goal", "Dream", "Focus", "Win", "Top", "Star", "Best", "Pro"]
    years = ["2024", "2025", "25"]
    numbers = [str(random.randint(10, 99)) for _ in range(3)]
    
    for pattern in patterns:
        for i in range(2):
            suggestion = pattern.format(
                year=random.choice(years),
                num=random.choice(numbers),
                word=random.choice(words)
            )
            suggestions.append(suggestion)
    
    return suggestions[:6]  # Return top 6 suggestions
