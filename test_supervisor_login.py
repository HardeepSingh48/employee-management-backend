#!/usr/bin/env python3
"""
Test script for supervisor login
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_supervisor_login():
    """Test supervisor login and verify response format"""
    
    print("Testing Supervisor Login...")
    print("=" * 50)
    
    # Test supervisor login
    login_data = {
        "email": "sup@company.com",  # Replace with actual supervisor email
        "password": "sup123"           # Replace with actual password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"User role: {result['data']['user']['role']}")
            print(f"Site ID: {result['data']['user'].get('site_id', 'Not set')}")
            print(f"Token: {result['data']['token'][:50]}...")
            
            # Verify the response structure
            user = result['data']['user']
            if user['role'] == 'supervisor':
                print("✅ User role is correctly set to 'supervisor'")
                if 'site_id' in user:
                    print(f"✅ Site ID is present: {user['site_id']}")
                else:
                    print("⚠️  Site ID is missing from response")
            else:
                print(f"❌ User role is {user['role']}, expected 'supervisor'")
                
        else:
            print(f"❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed.")

if __name__ == "__main__":
    test_supervisor_login()
