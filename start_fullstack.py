#!/usr/bin/env python3
"""
Full-stack startup script for NEET Practice Platform
Runs Django backend on port 8000 and React frontend on port 3000
"""
import os
import subprocess
import sys
import time
import signal
import threading

def start_django():
    """Start Django backend server"""
    os.chdir('backend')
    
    # Run Django server
    process = subprocess.Popen([
        sys.executable, 'manage.py', 'runserver', '0.0.0.0:8001'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Monitor Django output
    for line in iter(process.stdout.readline, b''):
        print(f"[DJANGO] {line.decode().strip()}")
    
    return process.returncode

def start_react():
    """Start React frontend server"""
    os.chdir('..')
    
    # Run React development server
    process = subprocess.Popen([
        'npm', 'run', 'dev'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Monitor React output
    for line in iter(process.stdout.readline, b''):
        print(f"[REACT] {line.decode().strip()}")
    
    return process.returncode

def main():
    print("Starting full-stack NEET Practice Platform...")
    
    # Start Django in background thread
    django_thread = threading.Thread(target=start_django)
    django_thread.daemon = True
    django_thread.start()
    
    # Give Django time to start
    time.sleep(3)
    
    # Start React in main thread
    try:
        start_react()
    except KeyboardInterrupt:
        print("\nShutting down...")
        subprocess.run(['pkill', '-f', 'python.*manage.py'], check=False)
        subprocess.run(['pkill', '-f', 'npm.*run.*dev'], check=False)

if __name__ == "__main__":
    main()