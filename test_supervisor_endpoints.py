#!/usr/bin/env python3
"""
Test script for supervisor endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_supervisor_endpoints():
    """Test the supervisor-specific endpoints"""
    
    print("Testing Supervisor Endpoints...")
    print("=" * 50)
    
    # Test 1: Get site employees (should fail without auth)
    print("\n1. Testing GET /api/employees/site_employees (no auth):")
    try:
        response = requests.get(f"{BASE_URL}/employees/site_employees")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Mark attendance (should fail without auth)
    print("\n2. Testing POST /api/attendance/mark (no auth):")
    try:
        data = {
            "employee_id": "910001",
            "attendance_date": "2024-08-24",
            "attendance_status": "Present"
        }
        response = requests.post(f"{BASE_URL}/attendance/mark", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Bulk attendance upload (should fail without auth)
    print("\n3. Testing POST /api/attendance/bulk-mark-excel (no auth):")
    try:
        data = {
            "month": "8",
            "year": "2024"
        }
        response = requests.post(f"{BASE_URL}/attendance/bulk-mark-excel", data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed. All endpoints should return 401 (Unauthorized) without proper authentication.")

if __name__ == "__main__":
    test_supervisor_endpoints()
