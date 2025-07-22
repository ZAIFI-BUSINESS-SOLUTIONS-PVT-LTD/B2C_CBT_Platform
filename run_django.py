#!/usr/bin/env python3
"""
Django runner that stays active
"""
import os
import subprocess
import sys

def main():
    os.chdir('backend')
    
    # Start Django on port 8001
    print("Starting Django on port 8001...")
    process = subprocess.run([
        sys.executable, 'manage.py', 'runserver', '0.0.0.0:8001'
    ])

if __name__ == "__main__":
    main()