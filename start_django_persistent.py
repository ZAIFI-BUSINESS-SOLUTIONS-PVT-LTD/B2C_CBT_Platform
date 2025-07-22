#!/usr/bin/env python3
"""
Persistent Django startup script for NEET Practice Platform
Keeps Django running on port 8001 and restarts it if it fails
"""
import os
import subprocess
import sys
import time
import signal
import threading

def start_django():
    """Start Django development server"""
    os.chdir('backend')
    process = subprocess.Popen([
        sys.executable, 'manage.py', 'runserver', '0.0.0.0:8001'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Monitor output
    for line in iter(process.stdout.readline, b''):
        print(line.decode().strip())
    
    return process.returncode

def main():
    """Main startup function"""
    print("Starting persistent Django server on port 8001...")
    
    # Set up signal handlers for graceful shutdown
    def cleanup(signum, frame):
        """Clean up processes on exit"""
        print(f"\nReceived signal {signum}, shutting down...")
        try:
            subprocess.run(['pkill', '-f', 'python.*manage.py'], check=False)
        except:
            pass
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Keep restarting Django if it fails
    while True:
        try:
            print("Starting Django server...")
            exit_code = start_django()
            print(f"Django server exited with code: {exit_code}")
            
            # If Django exits, wait a bit and restart
            time.sleep(2)
            print("Restarting Django server...")
            
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
            break
        except Exception as e:
            print(f"Error starting Django: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()