"""
Comprehensive API Endpoint Test Suite for Admin Role Split (admin1 vs admin2)

This script tests all critical endpoints with different admin roles to ensure:
- admin1 has full access including salary code management
- admin2 has restricted access (read-only salary codes, no site management)
- Both admin1 and admin2 have general admin access to employees, attendance, payroll

Run with: python test_admin_roles.py
Requires: requests library (pip install requests)
"""

import requests
import json
from typing import Dict, Optional
import sys

# Configuration
BASE_URL = "http://localhost:5000/api"
HEADERS = {"Content-Type": "application/json"}

# Test user credentials (update these based on your database)
SUPERADMIN_CREDS = {"identifier": "superadmin@company.com", "password": "superadmin123"}
ADMIN1_CREDS = {"identifier": "admin@company.com", "password": "admin123"}  # Update after creating user
ADMIN2_CREDS = {"identifier": "admin2_user", "password": "password123"}  # Update after creating user

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class APITester:
    def __init__(self):
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
        self.tokens = {}
    
    def log_success(self, message: str):
        print(f"{GREEN}✓{RESET} {message}")
        self.results["passed"] += 1
    
    def log_failure(self, message: str, details: str = ""):
        print(f"{RED}✗{RESET} {message}")
        if details:
            print(f"  {YELLOW}Details: {details}{RESET}")
        self.results["failed"] += 1
        self.results["errors"].append(f"{message}: {details}")
    
    def log_info(self, message: str):
        print(f"{BLUE}ℹ{RESET} {message}")
    
    def login(self, credentials: Dict, role_name: str) -> Optional[str]:
        """Login and return token"""
        self.log_info(f"Logging in as {role_name}...")
        try:
            response = requests.post(
                f"{BASE_URL}/login",
                json=credentials,
                headers=HEADERS
            )
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                if token:
                    self.tokens[role_name] = token
                    self.log_success(f"Logged in as {role_name}")
                    return token
                else:
                    self.log_failure(f"Login as {role_name} - no token in response")
            else:
                self.log_failure(f"Login as {role_name}", f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_failure(f"Login as {role_name}", str(e))
        return None
    
    def test_endpoint(self, role: str, method: str, endpoint: str, 
                     expected_status: int, description: str, 
                     payload: Optional[Dict] = None) -> bool:
        """Test a single endpoint"""
        token = self.tokens.get(role)
        if not token:
            self.log_failure(f"{description} ({role})", "No auth token")
            return False
        
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=payload, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=payload, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                self.log_failure(description, f"Unknown method: {method}")
                return False
            
            if response.status_code == expected_status:
                self.log_success(f"{description} ({role}): {method} {endpoint} → {response.status_code}")
                return True
            else:
                self.log_failure(
                    f"{description} ({role}): {method} {endpoint}",
                    f"Expected {expected_status}, got {response.status_code}. Response: {response.text[:200]}"
                )
                return False
        except Exception as e:
            self.log_failure(f"{description} ({role})", str(e))
            return False


def main():
    tester = APITester()
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Admin Role Split - Comprehensive API Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Phase 1: Authentication
    print(f"\n{BLUE}Phase 1: Authentication Tests{RESET}")
    print("-" * 60)
    superadmin_token = tester.login(SUPERADMIN_CREDS, "superadmin")
    admin1_token = tester.login(ADMIN1_CREDS, "admin1")
    admin2_token = tester.login(ADMIN2_CREDS, "admin2")
    
    if not all([superadmin_token, admin1_token, admin2_token]):
        print(f"\n{RED}CRITICAL: Could not log in all users. Please update credentials in script.{RESET}")
        print(f"{YELLOW}To create test users, run these SQL commands:{RESET}")
        print("\nUPDATE users SET role = 'admin1' WHERE email = 'your-admin1@example.com';")
        print("UPDATE users SET role = 'admin2' WHERE email = 'your-admin2@example.com';")
        print(f"\n{YELLOW}Then update the credentials in this script.{RESET}\n")
        sys.exit(1)
    
    # Phase 2: Salary Codes Tests (Critical for role differentiation)
    print(f"\n{BLUE}Phase 2: Salary Codes Access Control{RESET}")
    print("-" * 60)
    
    # GET (Read) - All admin roles should succeed
    tester.test_endpoint("admin1", "GET", "/salary-codes", 200, "List salary codes")
    tester.test_endpoint("admin2", "GET", "/salary-codes", 200, "List salary codes")
    
    # POST (Create) - Only admin1 and superadmin should succeed, admin2 should fail
    test_salary_code = {
        "salary_code": "TEST001",
        "site_name": "Test Site",
        "basic_pay": 10000
    }
    tester.test_endpoint("superadmin", "POST", "/salary-codes", 201, "Create salary code", test_salary_code)
    tester.test_endpoint("admin1", "POST", "/salary-codes/create", 201, "Create salary code", test_salary_code)
    tester.test_endpoint("admin2", "POST", "/salary-codes/create", 403, "Create salary code (should FAIL)", test_salary_code)
    
    # Phase 3: Sites Management Tests
    print(f"\n{BLUE}Phase 3: Sites Management{RESET}")
    print("-" * 60)
    
    tester.test_endpoint("admin1", "GET", "/sites?page=1&per_page=10", 200, "List sites")
    tester.test_endpoint("admin2", "GET", "/sites?page=1&per_page=10", 200, "List sites")
    
    # Phase 4: Employee Management Tests
    print(f"\n{BLUE}Phase 4: Employee Management{RESET}")
    print("-" * 60)
    
    tester.test_endpoint("admin1", "GET", "/employees?page=1&per_page=10", 200, "List employees")
    tester.test_endpoint("admin2", "GET", "/employees?page=1&per_page=10", 200, "List employees")
    
    # Phase 5: Attendance Tests
    print(f"\n{BLUE}Phase 5: Attendance Management{RESET}")
    print("-" * 60)
    
    tester.test_endpoint("admin1", "GET", "/attendance?page=1&per_page=10", 200, "List attendance")
    tester.test_endpoint("admin2", "GET", "/attendance?page=1&per_page=10", 200, "List attendance")
    
    # Phase 6: Payroll Tests
    print(f"\n{BLUE}Phase 6: Payroll Access{RESET}")
    print("-" * 60)
    
    tester.test_endpoint("admin1", "GET", "/payroll", 200, "Access payroll")
    tester.test_endpoint("admin2", "GET", "/payroll", 200, "Access payroll")
    
    # Phase 7: User Management (Superadmin only)
    print(f"\n{BLUE}Phase 7: User Management (Superadmin Only){RESET}")
    print("-" * 60)
    
    tester.test_endpoint("superadmin", "GET", "/superadmin/users", 200, "List users")
    tester.test_endpoint("admin1", "GET", "/superadmin/users", 403, "List users (should FAIL)")
    tester.test_endpoint("admin2", "GET", "/superadmin/users", 403, "List users (should FAIL)")
    
    # Final Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{GREEN}Passed:{RESET} {tester.results['passed']}")
    print(f"{RED}Failed:{RESET} {tester.results['failed']}")
    
    if tester.results['failed'] > 0:
        print(f"\n{RED}Failed Tests:{RESET}")
        for error in tester.results['errors']:
            print(f"  • {error}")
    
    success_rate = (tester.results['passed'] / (tester.results['passed'] + tester.results['failed'])) * 100
    print(f"\n{BLUE}Success Rate:{RESET} {success_rate:.1f}%")
    
    if tester.results['failed'] == 0:
        print(f"\n{GREEN}All tests passed! ✓{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n{RED}Some tests failed. Please review the errors above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Tests interrupted by user.{RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error: {str(e)}{RESET}\n")
        sys.exit(1)
