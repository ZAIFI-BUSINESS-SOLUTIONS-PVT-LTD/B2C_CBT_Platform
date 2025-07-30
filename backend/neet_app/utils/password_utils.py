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
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    else:
        strength_score += 20
    
    # Check maximum length
    if len(password) > 64:
        errors.append("Password must be no more than 64 characters long")
        return False, errors, 0
    
    # Check for lowercase letters
    if re.search(r'[a-z]', password):
        strength_score += 15
    else:
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for uppercase letters
    if re.search(r'[A-Z]', password):
        strength_score += 15
    else:
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for numbers
    if re.search(r'\d', password):
        strength_score += 15
    else:
        errors.append("Password must contain at least one number")
    
    # Check for special characters
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        strength_score += 15
    else:
        errors.append("Password must contain at least one special character")
    
    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common. Please choose a more unique password")
        strength_score = max(0, strength_score - 30)
    
    # Bonus points for length
    if len(password) >= 12:
        strength_score += 10
    if len(password) >= 16:
        strength_score += 10
    
    # Check for repeated characters
    if len(set(password)) < len(password) * 0.6:
        errors.append("Password has too many repeated characters")
        strength_score = max(0, strength_score - 20)
    
    # Ensure score doesn't exceed 100
    strength_score = min(100, strength_score)
    
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


def validate_full_name_uniqueness(full_name: str, exclude_student_id: str = None) -> Tuple[bool, str]:
    """
    Validate full_name uniqueness (case-insensitive)
    
    Args:
        full_name (str): Full name to check
        exclude_student_id (str): Student ID to exclude from check (for updates)
        
    Returns:
        Tuple[bool, str]: (is_unique, error_message)
    """
    from ..models import StudentProfile
    
    # Case-insensitive check
    query = StudentProfile.objects.filter(full_name__iexact=full_name)
    
    # Exclude current student if updating
    if exclude_student_id:
        query = query.exclude(student_id=exclude_student_id)
    
    if query.exists():
        return False, "This username is already taken. Please choose a different name."
    
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
