#!/usr/bin/env python
"""
Test script to debug JWT authentication issues
"""
import os
import django
import sys
import requests

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.authentication import StudentTokenObtainPairSerializer

def test_api_authentication():
    """Test JWT authentication with actual API calls"""
    print("=== Testing API Authentication ===")
    
    # 1. Get JWT token
    login_data = {
        'email': 'vishal247000@gmail.com',
        'password': 'VISH2407'
    }
    
    try:
        # Get token using API
        response = requests.post('http://127.0.0.1:8000/api/auth/login/', json=login_data)
        print(f"Login API Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access']
            print(f"Access token received: {access_token[:50]}...")
            
            # 2. Test authenticated request
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Test dashboard analytics
            dashboard_response = requests.get('http://127.0.0.1:8000/api/dashboard/analytics/', headers=headers)
            print(f"Dashboard API Status: {dashboard_response.status_code}")
            
            if dashboard_response.status_code == 200:
                print("✅ Dashboard access successful")
            else:
                print(f"❌ Dashboard access failed: {dashboard_response.text}")
            
            # Test test sessions list
            sessions_response = requests.get('http://127.0.0.1:8000/api/test-sessions/', headers=headers)
            print(f"Test Sessions List Status: {sessions_response.status_code}")
            
            if sessions_response.status_code == 200:
                sessions_data = sessions_response.json()
                print(f"✅ Test sessions access successful - found {len(sessions_data)} sessions")
                
                # Test accessing specific sessions
                if sessions_data and len(sessions_data) > 0:
                    # Test first session
                    first_session = sessions_data[0]
                    session_id = first_session['id']
                    session_response = requests.get(f'http://127.0.0.1:8000/api/test-sessions/{session_id}/', headers=headers)
                    print(f"Session {session_id} Status: {session_response.status_code}")
                    
                    if session_response.status_code == 200:
                        print(f"✅ Session {session_id} access successful")
                    else:
                        print(f"❌ Session {session_id} access failed: {session_response.text}")
                        
                    # Test creating a new session
                    create_data = {
                        "selectedTopics": ["137", "138"],
                        "timeLimit": 10,
                        "questionCount": 5
                    }
                    create_response = requests.post('http://127.0.0.1:8000/api/test-sessions/', json=create_data, headers=headers)
                    print(f"Create Session Status: {create_response.status_code}")
                    
                    if create_response.status_code == 201:
                        new_session = create_response.json()
                        new_session_id = new_session['id']
                        print(f"✅ New session created with ID: {new_session_id}")
                        
                        # Test accessing the newly created session
                        new_session_response = requests.get(f'http://127.0.0.1:8000/api/test-sessions/{new_session_id}/', headers=headers)
                        print(f"New Session Access Status: {new_session_response.status_code}")
                        
                        if new_session_response.status_code == 200:
                            print(f"✅ New session {new_session_id} access successful")
                        else:
                            print(f"❌ New session {new_session_id} access failed: {new_session_response.text}")
                    else:
                        print(f"❌ Session creation failed: {create_response.text}")
                        
            else:
                print(f"❌ Test sessions access failed: {sessions_response.text}")
                
        else:
            print(f"❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_authentication()
