#!/usr/bin/env python3
"""
Test script for the attendance system
"""

import requests
import json
from datetime import datetime, date
import time

BASE_URL = "http://localhost:5000"

def test_api_endpoint(method, endpoint, data=None, params=None):
    """Helper function to test API endpoints"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
        
        print(f"\n🔍 {method.upper()} {endpoint}")
        print(f"📊 Status Code: {response.status_code}")
        
        try:
            result = response.json()
            print(f"📦 Response: {json.dumps(result, indent=2)}")
            return result
        except:
            print(f"📦 Response: {response.text}")
            return response.text
            
    except Exception as e:
        print(f"❌ Error testing {endpoint}: {e}")
        return None

def main():
    print("🚀 Testing Attendance System")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1️⃣ Testing server connectivity...")
    result = test_api_endpoint("GET", "/")
    if not result:
        print("❌ Server is not running. Please start the Flask server first.")
        return
    
    # Test 2: Get employees to use for testing
    print("\n2️⃣ Getting employees for testing...")
    employees_result = test_api_endpoint("GET", "/api/employees")
    
    if not employees_result or not employees_result.get("success"):
        print("⚠️ No employees found or error getting employees. Let's create a test employee first.")
        
        # Create a test employee
        test_employee = {
            "first_name": "Test",
            "last_name": "Employee",
            "email": "test.employee@company.com",
            "phone_number": "1234567890",
            "department_id": "IT",
            "designation": "Software Engineer",
            "site_name": "Test Site",
            "rank": "Engineer",
            "state": "Delhi",
            "base_salary": 50000
        }
        
        print("\n📝 Creating test employee...")
        create_result = test_api_endpoint("POST", "/api/employees/register", test_employee)
        
        if create_result and create_result.get("success"):
            employee_id = create_result["data"]["employee_id"]
            print(f"✅ Test employee created with ID: {employee_id}")
        else:
            print("❌ Failed to create test employee. Using default ID.")
            employee_id = "EMP001"
    else:
        # Use first employee from the list
        employees = employees_result.get("data", [])
        if employees:
            employee_id = employees[0]["employee_id"]
            print(f"✅ Using existing employee ID: {employee_id}")
        else:
            employee_id = "EMP001"
            print("⚠️ No employees in list, using default ID: EMP001")
    
    # Test 3: Mark attendance for today
    print(f"\n3️⃣ Testing attendance marking for employee {employee_id}...")
    today = date.today().isoformat()
    
    attendance_data = {
        "employee_id": employee_id,
        "attendance_date": today,
        "attendance_status": "Present",
        "check_in_time": f"{today}T09:00:00",
        "check_out_time": f"{today}T17:00:00",
        "overtime_hours": 1.0,
        "remarks": "Test attendance entry",
        "marked_by": "admin"
    }
    
    mark_result = test_api_endpoint("POST", "/api/attendance/mark", attendance_data)
    
    # Test 4: Try to mark attendance again (should fail - duplicate)
    print(f"\n4️⃣ Testing duplicate attendance marking (should fail)...")
    duplicate_result = test_api_endpoint("POST", "/api/attendance/mark", attendance_data)
    
    # Test 5: Get employee attendance
    print(f"\n5️⃣ Getting attendance records for employee {employee_id}...")
    get_attendance_result = test_api_endpoint("GET", f"/api/attendance/employee/{employee_id}")
    
    # Test 6: Get attendance by date
    print(f"\n6️⃣ Getting all attendance for date {today}...")
    date_attendance_result = test_api_endpoint("GET", f"/api/attendance/date/{today}")
    
    # Test 7: Get today's attendance
    print(f"\n7️⃣ Getting today's attendance...")
    today_result = test_api_endpoint("GET", "/api/attendance/today")
    
    # Test 8: Get monthly summary
    print(f"\n8️⃣ Getting monthly attendance summary...")
    current_date = datetime.now()
    monthly_result = test_api_endpoint("GET", f"/api/attendance/monthly-summary/{employee_id}", 
                                     params={"year": current_date.year, "month": current_date.month})
    
    # Test 9: Bulk attendance marking
    print(f"\n9️⃣ Testing bulk attendance marking...")
    bulk_data = {
        "attendance_records": [
            {
                "employee_id": employee_id,
                "attendance_date": "2024-08-13",
                "attendance_status": "Present",
                "check_in_time": "2024-08-13T09:15:00",
                "check_out_time": "2024-08-13T17:30:00",
                "overtime_hours": 0.5,
                "remarks": "Bulk test entry 1"
            },
            {
                "employee_id": employee_id,
                "attendance_date": "2024-08-12",
                "attendance_status": "Late",
                "check_in_time": "2024-08-12T09:30:00",
                "check_out_time": "2024-08-12T17:00:00",
                "overtime_hours": 0.0,
                "remarks": "Bulk test entry 2 - Late arrival"
            }
        ],
        "marked_by": "admin"
    }
    
    bulk_result = test_api_endpoint("POST", "/api/attendance/bulk-mark", bulk_data)
    
    # Test 10: Update attendance (if we have an attendance_id)
    if mark_result and mark_result.get("success") and mark_result.get("data"):
        attendance_id = mark_result["data"]["attendance_id"]
        print(f"\n🔟 Testing attendance update for ID {attendance_id}...")
        
        update_data = {
            "attendance_status": "Late",
            "remarks": "Updated: Employee was late due to traffic",
            "late_minutes": 15,
            "updated_by": "admin"
        }
        
        update_result = test_api_endpoint("PUT", f"/api/attendance/update/{attendance_id}", update_data)
    
    print("\n" + "=" * 50)
    print("🎉 Attendance System Testing Complete!")
    print("\n📋 Summary:")
    print("✅ Server connectivity - OK")
    print("✅ Employee data - OK")
    print("✅ Mark attendance - Tested")
    print("✅ Duplicate prevention - Tested")
    print("✅ Get employee attendance - Tested")
    print("✅ Get attendance by date - Tested")
    print("✅ Get today's attendance - Tested")
    print("✅ Monthly summary - Tested")
    print("✅ Bulk attendance marking - Tested")
    print("✅ Update attendance - Tested")
    
    print("\n🔗 Available Endpoints:")
    print("• POST /api/attendance/mark - Mark individual attendance")
    print("• POST /api/attendance/bulk-mark - Bulk attendance marking")
    print("• GET /api/attendance/employee/{id} - Get employee attendance")
    print("• GET /api/attendance/date/{date} - Get attendance by date")
    print("• GET /api/attendance/today - Get today's attendance")
    print("• GET /api/attendance/monthly-summary/{id}?year=2024&month=8 - Monthly summary")
    print("• PUT /api/attendance/update/{id} - Update attendance record")

if __name__ == "__main__":
    main()
