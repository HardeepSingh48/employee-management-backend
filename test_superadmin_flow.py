#!/usr/bin/env python3
"""
Test script to verify superadmin functionality end-to-end
"""
import requests
import json
import time

def test_superadmin_flow():
    """Test the complete superadmin flow"""
    print("🧪 Testing Superadmin Flow")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    
    # Step 1: Test server connectivity
    print("\n1️⃣ Testing server connectivity...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.ok:
            print("✅ Server is running")
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        print("💡 Start the backend server first: cd employee-management-backend && python app.py")
        return False
    
    # Step 2: Test superadmin login
    print("\n2️⃣ Testing superadmin login...")
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
        
        if response.ok:
            data = response.json()
            if data.get('success') and 'token' in data.get('data', {}):
                token = data['data']['token']
                user_role = data['data']['user']['role']
                print(f"✅ Login successful - Role: {user_role}")
                
                if user_role != 'superadmin':
                    print(f"❌ Expected superadmin role, got: {user_role}")
                    return False
                    
                return token
            else:
                print(f"❌ Login response invalid: {data}")
                return False
        else:
            print(f"❌ Login failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False
    
def test_user_management(token):
    """Test user management endpoints"""
    print("\n3️⃣ Testing user management endpoints...")
    
    base_url = "http://127.0.0.1:5000"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:3000'
    }
    
    # Test GET users
    try:
        response = requests.get(
            f"{base_url}/api/superadmin/users",
            headers=headers,
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            print(f"✅ Get users successful - Found {len(data.get('data', []))} users")
        else:
            print(f"❌ Get users failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Get users test failed: {e}")
        return False
    
    # Test CREATE user
    print("\n4️⃣ Testing user creation...")
    try:
        test_user_data = {
            "name": "Test Admin",
            "email": f"test_admin_{int(time.time())}@company.com",
            "password": "testpass123",
            "role": "admin"
        }
        
        response = requests.post(
            f"{base_url}/api/superadmin/users",
            json=test_user_data,
            headers=headers,
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            print(f"✅ User creation successful: {data.get('message')}")
        else:
            print(f"❌ User creation failed - Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ User creation test failed: {e}")
        return False
    
    return True

def main():
    """Run complete test suite"""
    print("🧪 Superadmin Flow Test Suite")
    print(f"⏰ Started at: {datetime.now()}")
    print("=" * 60)
    
    # Test login and get token
    token = test_superadmin_flow()
    if not token:
        print("\n❌ Test suite failed at login step")
        return False
    
    # Test user management
    if test_user_management(token):
        print("\n🎉 All tests passed!")
        print("✅ Superadmin functionality is working correctly")
        return True
    else:
        print("\n❌ Test suite failed at user management step")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)