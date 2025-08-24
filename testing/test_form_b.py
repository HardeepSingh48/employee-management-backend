#!/usr/bin/env python3
"""
Test script for Form B (Wages Register) integration
This script tests the Form B API endpoints to ensure they work correctly.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Adjust if your backend runs on a different port
API_BASE = f"{BASE_URL}/api"

def test_form_b_data_endpoint():
    """Test the Form B data retrieval endpoint"""
    print("🧪 Testing Form B data endpoint...")
    
    # Test parameters
    params = {
        'year': 2024,
        'month': 12,
        # 'site': 'VADHWAN-GDC-DELUX-BEARING-PVT-LTD'  # Optional
    }
    
    try:
        response = requests.get(f"{API_BASE}/forms/form-b", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Form B data endpoint successful!")
            print(f"   - Found {len(data.get('data', []))} employees")
            print(f"   - Total earnings: {data.get('totals', {}).get('totalEarnings', 0)}")
            print(f"   - Total net payable: {data.get('totals', {}).get('totalNetPayable', 0)}")
            return True
        else:
            print(f"❌ Form B data endpoint failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Make sure the backend is running.")
        return False
    except Exception as e:
        print(f"❌ Error testing Form B data endpoint: {str(e)}")
        return False

def test_form_b_download_endpoint():
    """Test the Form B Excel download endpoint"""
    print("\n🧪 Testing Form B download endpoint...")
    
    # Test parameters
    params = {
        'year': 2024,
        'month': 12,
        # 'site': 'VADHWAN-GDC-DELUX-BEARING-PVT-LTD'  # Optional
    }
    
    try:
        response = requests.get(f"{API_BASE}/forms/form-b/download", params=params)
        
        if response.status_code == 200:
            # Check if response is Excel file
            content_type = response.headers.get('content-type', '')
            if 'spreadsheet' in content_type or 'excel' in content_type:
                print("✅ Form B download endpoint successful!")
                print(f"   - Content type: {content_type}")
                print(f"   - File size: {len(response.content)} bytes")
                
                # Optionally save the file for manual inspection
                filename = f"test_form_b_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"   - Saved test file as: {filename}")
                return True
            else:
                print(f"❌ Form B download endpoint returned unexpected content type: {content_type}")
                print(f"   Response: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Form B download endpoint failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Make sure the backend is running.")
        return False
    except Exception as e:
        print(f"❌ Error testing Form B download endpoint: {str(e)}")
        return False

def test_backend_health():
    """Test if the backend is running and healthy"""
    print("🧪 Testing backend health...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            print("✅ Backend is healthy!")
            return True
        else:
            print(f"❌ Backend health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to backend. Make sure the backend is running.")
        return False
    except Exception as e:
        print(f"❌ Error testing backend health: {str(e)}")
        return False

def main():
    """Run all Form B integration tests"""
    print("🚀 Starting Form B Integration Tests")
    print("=" * 50)
    
    # Test backend health first
    if not test_backend_health():
        print("\n❌ Backend is not available. Please start the backend and try again.")
        return
    
    # Test Form B endpoints
    data_test_passed = test_form_b_data_endpoint()
    download_test_passed = test_form_b_download_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   - Backend Health: ✅")
    print(f"   - Form B Data Endpoint: {'✅' if data_test_passed else '❌'}")
    print(f"   - Form B Download Endpoint: {'✅' if download_test_passed else '❌'}")
    
    if data_test_passed and download_test_passed:
        print("\n🎉 All Form B integration tests passed!")
        print("\n📝 Next steps:")
        print("   1. Test the frontend Form B tab in your browser")
        print("   2. Verify data consistency between table display and Excel download")
        print("   3. Test with different year/month/site combinations")
    else:
        print("\n⚠️  Some tests failed. Please check the backend logs and fix any issues.")

if __name__ == "__main__":
    main()
