#!/usr/bin/env python3
"""
Comprehensive Backend Diagnostics Script
Tests all API endpoints to identify deployment issues
"""

import requests
import json
import sys
from datetime import datetime, date
from typing import Dict, List, Any

# Configuration
LOCAL_BASE_URL = "http://localhost:5000"
DEPLOYED_BASE_URL = "https://employee-management-backend-kwtq.onrender.com"

class BackendDiagnostics:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.results = []
        self.session = requests.Session()
        
    def log_result(self, endpoint: str, method: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        # Print result
        status_emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_emoji} {method} {endpoint} - {status}")
        if details:
            print(f"   {details}")
    
    def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, 
                     expected_status: int = 200, auth_token: str = None) -> bool:
        """Test a single endpoint"""
        url = f"{self.api_base}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                self.log_result(endpoint, method, "FAIL", f"Unsupported method: {method}")
                return False
            
            if response.status_code == expected_status:
                try:
                    response_data = response.json()
                    if response_data.get('success', True):
                        self.log_result(endpoint, method, "PASS", 
                                      f"Status: {response.status_code}, Data: {len(str(response_data))} chars")
                        return True
                    else:
                        self.log_result(endpoint, method, "FAIL", 
                                      f"API returned success=false: {response_data.get('message', 'No message')}")
                        return False
                except json.JSONDecodeError:
                    self.log_result(endpoint, method, "PASS", 
                                  f"Status: {response.status_code}, Non-JSON response")
                    return True
            else:
                self.log_result(endpoint, method, "FAIL", 
                              f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_result(endpoint, method, "FAIL", "Connection error - server may be down")
            return False
        except requests.exceptions.Timeout:
            self.log_result(endpoint, method, "FAIL", "Request timeout")
            return False
        except Exception as e:
            self.log_result(endpoint, method, "FAIL", f"Unexpected error: {str(e)}")
            return False
    
    def test_basic_connectivity(self):
        """Test basic server connectivity"""
        print("\n🔍 Testing Basic Connectivity...")
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                self.log_result("/", "GET", "PASS", f"Server is responding")
                return True
            else:
                self.log_result("/", "GET", "FAIL", f"Server returned {response.status_code}")
                return False
        except Exception as e:
            self.log_result("/", "GET", "FAIL", f"Cannot connect to server: {str(e)}")
            return False
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test login endpoint structure (without valid credentials)
        self.test_endpoint("/auth/login", "POST", 
                          {"email": "test@test.com", "password": "test"}, 
                          expected_status=401)
        
        # Test register endpoint structure (should fail validation)
        self.test_endpoint("/auth/register", "POST", 
                          {"email": "invalid"}, 
                          expected_status=400)
    
    def test_employee_endpoints(self):
        """Test employee management endpoints"""
        print("\n👥 Testing Employee Endpoints...")
        
        # Test get all employees
        self.test_endpoint("/employees/all", "GET")
        
        # Test employee list with pagination
        self.test_endpoint("/employees/list", "GET")
        
        # Test employee registration (should fail validation)
        self.test_endpoint("/employees/register", "POST", 
                          {"first_name": "Test"}, 
                          expected_status=400)
    
    def test_department_endpoints(self):
        """Test department endpoints"""
        print("\n🏢 Testing Department Endpoints...")
        
        # Test get departments
        self.test_endpoint("/departments", "GET")
    
    def test_salary_code_endpoints(self):
        """Test salary code endpoints"""
        print("\n💰 Testing Salary Code Endpoints...")
        
        # Test get salary codes
        self.test_endpoint("/salary-codes", "GET")
    
    def test_attendance_endpoints(self):
        """Test attendance endpoints"""
        print("\n📅 Testing Attendance Endpoints...")
        
        # Test mark attendance (should fail validation)
        self.test_endpoint("/attendance/mark", "POST", 
                          {"employee_id": "invalid"}, 
                          expected_status=400)
    
    def test_forms_endpoints(self):
        """Test forms endpoints"""
        print("\n📋 Testing Forms Endpoints...")
        
        # Test Form B data
        self.test_endpoint("/forms/form-b?year=2025&month=7", "GET")
        
        # Test Form B download
        self.test_endpoint("/forms/form-b/download?year=2025&month=7", "GET")
    
    def test_salary_endpoints(self):
        """Test salary calculation endpoints"""
        print("\n💵 Testing Salary Endpoints...")
        
        # Test salary calculation (should fail validation)
        self.test_endpoint("/salary/calculate-monthly", "POST", 
                          {"year": 2025, "month": 7}, 
                          expected_status=400)
    
    def run_all_tests(self):
        """Run all diagnostic tests"""
        print(f"\n🚀 Starting Comprehensive Backend Diagnostics for: {self.base_url}")
        print("=" * 80)
        
        # Test basic connectivity first
        if not self.test_basic_connectivity():
            print("\n❌ Basic connectivity failed. Stopping tests.")
            return False
        
        # Run all endpoint tests
        self.test_auth_endpoints()
        self.test_employee_endpoints()
        self.test_department_endpoints()
        self.test_salary_code_endpoints()
        self.test_attendance_endpoints()
        self.test_forms_endpoints()
        self.test_salary_endpoints()
        
        # Summary
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.results if r['status'] == 'FAIL'])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['method']} {result['endpoint']}: {result['details']}")

def main():
    """Main function"""
    print("Employee Management System - Backend Diagnostics")
    print("=" * 60)
    
    # Test both local and deployed backends
    environments = [
        ("LOCAL", LOCAL_BASE_URL),
        ("DEPLOYED", DEPLOYED_BASE_URL)
    ]
    
    all_results = {}
    
    for env_name, base_url in environments:
        print(f"\n🌐 Testing {env_name} Environment: {base_url}")
        diagnostics = BackendDiagnostics(base_url)
        diagnostics.run_all_tests()
        all_results[env_name] = diagnostics.results
    
    # Compare results
    print("\n" + "=" * 80)
    print("🔍 ENVIRONMENT COMPARISON")
    print("=" * 80)
    
    local_results = all_results.get("LOCAL", [])
    deployed_results = all_results.get("DEPLOYED", [])
    
    local_passed = len([r for r in local_results if r['status'] == 'PASS'])
    deployed_passed = len([r for r in deployed_results if r['status'] == 'PASS'])
    
    print(f"Local Environment: {local_passed}/{len(local_results)} tests passed")
    print(f"Deployed Environment: {deployed_passed}/{len(deployed_results)} tests passed")
    
    if local_passed > deployed_passed:
        print("\n⚠️  Deployed environment has more failures than local!")
        print("This suggests deployment-specific issues.")

if __name__ == "__main__":
    main()
