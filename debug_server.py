#!/usr/bin/env python3
"""
Debug script to test Flask server connectivity and CORS configuration
"""
import requests
import json
import sys
from datetime import datetime

def test_server_connectivity():
    """Test basic server connectivity"""
    print("🔍 Testing Flask Server Connectivity...")
    print("=" * 50)
    
    base_urls = [
        "http://localhost:5000",
        "http://127.0.0.1:5000"
    ]
    
    for base_url in base_urls:
        print(f"\n📡 Testing {base_url}")
        try:
            # Test root endpoint
            response = requests.get(f"{base_url}/", timeout=5)
            print(f"✅ Root endpoint: {response.status_code} - {response.json()}")
            
            # Test health endpoint
            response = requests.get(f"{base_url}/health", timeout=5)
            print(f"✅ Health endpoint: {response.status_code} - {response.json()}")
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - Server not running on {base_url}")
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout - Server slow to respond on {base_url}")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_cors_preflight():
    """Test CORS preflight requests"""
    print("\n🌐 Testing CORS Preflight Requests...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    endpoints = [
        "/api/auth/login",
        "/api/superadmin/users"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing CORS for {endpoint}")
        try:
            # Simulate preflight request
            headers = {
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'Content-Type,Authorization'
            }
            
            response = requests.options(f"{base_url}{endpoint}", headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            print(f"CORS Headers: {dict(response.headers)}")
            
            # Check required CORS headers
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            for header, value in cors_headers.items():
                status = "✅" if value else "❌"
                print(f"{status} {header}: {value}")
                
        except Exception as e:
            print(f"❌ CORS test failed: {e}")

def test_api_endpoints():
    """Test actual API endpoints"""
    print("\n🔌 Testing API Endpoints...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:5000"
    
    # Test login endpoint
    print("\n🔐 Testing Login Endpoint")
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
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'token' in data['data']:
                token = data['data']['token']
                print("✅ Login successful, testing authenticated endpoint...")
                
                # Test superadmin endpoint with token
                auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'Origin': 'http://localhost:3000'
                }
                
                response = requests.get(
                    f"{base_url}/api/superadmin/users",
                    headers=auth_headers,
                    timeout=10
                )
                
                print(f"Superadmin endpoint status: {response.status_code}")
                print(f"Superadmin response: {response.text[:200]}...")
                
    except Exception as e:
        print(f"❌ API test failed: {e}")

def main():
    print("🚀 Flask Backend Debug Tool")
    print(f"⏰ Started at: {datetime.now()}")
    print("=" * 60)
    
    test_server_connectivity()
    test_cors_preflight()
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("🏁 Debug complete!")
    print("\n💡 If tests fail:")
    print("1. Make sure Flask server is running: python app.py")
    print("2. Check if port 5000 is available")
    print("3. Verify database connection in config.py")
    print("4. Check firewall/antivirus blocking port 5000")

if __name__ == "__main__":
    main()