#!/usr/bin/env python3
"""
Simple Django backend runner for NEET Practice Platform
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    print("🏥 Starting Django NEET Practice Platform Backend...")
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
    
    # Change to backend directory
    os.chdir('backend')
    
    try:
        # Start the development server
        print("🚀 Django backend starting on http://0.0.0.0:8000")
        execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8000'])
        
    except Exception as e:
        print(f"❌ Error starting Django: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()