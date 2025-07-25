#!/usr/bin/env python
"""
Test script to reproduce the 401 error in test session retrieval
"""
import os
import django
import sys
import requests
import time

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

def test_session_retrieval_issue():
    """Test the specific issue with test session retrieval"""
    print("=== Testing Session Retrieval Issue ===")
    
    # 1. Login and get token
    login_data = {
        'email': 'vishal247000@gmail.com',
        'password': 'VISH2407'
    }
    
    login_response = requests.post('http://127.0.0.1:8000/api/auth/login/', json=login_data)
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token_data = login_response.json()
    access_token = token_data['access']
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"✅ Login successful, token: {access_token[:50]}...")
    
    # 2. Create a new test session
    create_data = {
        "selectedTopics": ["137", "138"],
        "timeLimit": 10,
        "questionCount": 5
    }
    
    create_response = requests.post('http://127.0.0.1:8000/api/test-sessions/', json=create_data, headers=headers)
    if create_response.status_code != 201:
        print(f"❌ Session creation failed: {create_response.text}")
        return
    
    new_session = create_response.json()
    print(f"Session creation response keys: {new_session.keys()}")
    
    # Extract session ID from the nested structure
    if 'session' in new_session and 'id' in new_session['session']:
        session_id = new_session['session']['id']
    else:
        # Fallback to check other possible locations
        session_id = new_session.get('id') or new_session.get('sessionId')
        
    if not session_id:
        print(f"❌ No session ID found in response")
        return
        
    print(f"✅ Session created with ID: {session_id}")
    
    # 3. Test immediate retrieval (first GET)
    print("\n--- First GET request ---")
    first_response = requests.get(f'http://127.0.0.1:8000/api/test-sessions/{session_id}/', headers=headers)
    print(f"First request status: {first_response.status_code}")
    
    if first_response.status_code == 200:
        print("✅ First request successful")
    else:
        print(f"❌ First request failed: {first_response.text}")
    
    # 4. Small delay and test second retrieval (second GET)
    print("\n--- Second GET request (after small delay) ---")
    time.sleep(0.1)  # Small delay to simulate frontend behavior
    
    second_response = requests.get(f'http://127.0.0.1:8000/api/test-sessions/{session_id}/', headers=headers)
    print(f"Second request status: {second_response.status_code}")
    
    if second_response.status_code == 200:
        print("✅ Second request successful")
    else:
        print(f"❌ Second request failed: {second_response.text}")
    
    # 5. Test immediate consecutive requests (like frontend might do)
    print("\n--- Multiple consecutive requests ---")
    for i in range(3):
        response = requests.get(f'http://127.0.0.1:8000/api/test-sessions/{session_id}/', headers=headers)
        print(f"Request {i+1} status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Failed: {response.text}")

if __name__ == "__main__":
    test_session_retrieval_issue()
