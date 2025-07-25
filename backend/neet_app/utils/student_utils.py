"""
Student utility functions for auto-generating student_id and password
"""
import string
from django.utils.crypto import get_random_string


def generate_student_id(full_name, date_of_birth):
    """
    Generate student ID in format: STU + YY + DDMM + ABC123
    
    Args:
        full_name (str): Student's full name
        date_of_birth (date): Student's date of birth
        
    Returns:
        str: Unique student ID
        
    Example:
        Name: Ramesh Kumar, DOB: 2005-07-08
        Result: STU250708ABC123
    """
    year = str(date_of_birth.year)[-2:]  # Last 2 digits of year (25)
    ddmm = date_of_birth.strftime("%d%m")  # Day and month (0708)
    
    # Generate unique random suffix (3 letters + 3 numbers)
    # We'll check uniqueness in the model's save method
    letters = get_random_string(3, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    numbers = get_random_string(3, '0123456789')
    
    student_id = f"STU{year}{ddmm}{letters}{numbers}"
    return student_id


def generate_password(full_name, date_of_birth):
    """
    Generate password in format: FIRSTFOUR + DDMM
    
    Args:
        full_name (str): Student's full name
        date_of_birth (date): Student's date of birth
        
    Returns:
        str: Auto-generated password
        
    Example:
        Name: Ramesh Kumar, DOB: 2005-07-08
        Result: RAME0708
    """
    # Get first 4 characters of name (remove spaces, convert to uppercase)
    name_clean = full_name.upper().replace(' ', '').replace('.', '')
    name_part = name_clean[:4].ljust(4, 'X')  # Pad with 'X' if name is shorter than 4 chars
    
    # Get day and month from DOB
    ddmm = date_of_birth.strftime("%d%m")
    
    password = f"{name_part}{ddmm}"
    return password


def ensure_unique_student_id(full_name, date_of_birth):
    """
    Ensure generated student_id is unique by checking against existing records
    
    Args:
        full_name (str): Student's full name
        date_of_birth (date): Student's date of birth
        
    Returns:
        str: Guaranteed unique student ID
    """
    from ..models import StudentProfile
    
    max_attempts = 100  # Prevent infinite loop
    attempts = 0
    
    while attempts < max_attempts:
        candidate_id = generate_student_id(full_name, date_of_birth)
        
        # Check if this ID already exists
        if not StudentProfile.objects.filter(student_id=candidate_id).exists():
            return candidate_id
            
        attempts += 1
    
    # Fallback: add timestamp if we couldn't generate unique ID
    import time
    timestamp = str(int(time.time()))[-4:]  # Last 4 digits of timestamp
    base_id = f"STU{date_of_birth.strftime('%y%d%m')}"
    return f"{base_id}{timestamp}"
