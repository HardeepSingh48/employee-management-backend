#!/usr/bin/env python3
"""
Simple test script to verify superadmin login
"""
import requests
import json

def test_superadmin_login():
    """Test superadmin login"""
    print("Testing Superadmin Login")
    print("=" * 30)

    base_url = "http://127.0.0.1:5000"

    # Test server connectivity
    print("Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.ok:
            print("Server is running")
        else:
            print(f"Server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"Server not reachable: {e}")
        return False

    # Test superadmin login
    print("Testing superadmin login...")
    try:
        login_data = {
            "email": "superadmin@company.com",
            "password": "superadmin123"
        }

        headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000'
        }

        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers=headers,
            timeout=10
        )

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")

        if response.ok:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")

            if data.get('success') and 'token' in data.get('data', {}):
                token = data['data']['token']
                user = data['data']['user']
                user_role = user.get('role')
                print(f"Login successful - Role: {user_role}")

                if user_role != 'superadmin':
                    print(f"ERROR: Expected superadmin role, got: {user_role}")
                    return False

                print("SUCCESS: Superadmin login works correctly")
                return True
            else:
                print(f"ERROR: Login response invalid: {data}")
                return False
        else:
            print(f"ERROR: Login failed - Status: {response.status_code}")
            print(f"Response text: {response.text}")
            return False

    except Exception as e:
        print(f"ERROR: Login test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_superadmin_login()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")