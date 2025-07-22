#!/usr/bin/env python3
"""
Django startup script for the NEET Practice Platform
"""
import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def main():
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
    
    # Change to backend directory
    os.chdir('backend')
    
    print("Starting Django NEET Practice Platform...")
    
    try:
        # Run migrations
        print("Running database migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        # Populate initial data
        print("Populating initial data...")
        execute_from_command_line(['manage.py', 'populate_data'])
        
        # Create superuser if needed (optional)
        print("Django setup complete!")
        
        # Start the development server
        print("Starting Django development server on port 8000...")
        execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
        
    except Exception as e:
        print(f"Error starting Django: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()