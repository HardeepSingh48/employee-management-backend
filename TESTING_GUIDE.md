# Admin Role Testing Guide

## Quick Start

### 1. Create Test Users

First, you need to create or promote users to admin1 and admin2 roles in your database:

```sql
-- Promote existing admin users to admin1 (full access)
UPDATE users SET role = 'admin1' WHERE email = 'admin1@example.com';

-- Promote existing admin users to admin2 (restricted access)
UPDATE users SET role = 'admin2' WHERE email = 'admin2@example.com';
```

### 2. Update Test Credentials

Edit `test_admin_roles.py` and update the credentials on lines 18-20:

```python
ADMIN1_CREDS = {"username": "your_admin1_username", "password": "your_password"}
ADMIN2_CREDS = {"username": "your_admin2_username", "password": "your_password"}
```

### 3. Install Dependencies

```bash
pip install requests
```

### 4. Run Tests

```bash
# Make sure your backend server is running on http://localhost:5000
python test_admin_roles.py
```

## What Gets Tested

### ✅ Authentication
- Login for superadmin, admin1, admin2

### ✅ Salary Codes (Critical for Role Differentiation)
- **admin1**: Can CREATE, READ, UPDATE, DELETE
- **admin2**: Can READ only (403 on CREATE/UPDATE/DELETE)
- **superadmin**: Full access

### ✅ General Admin Operations
Both admin1 and admin2 should have access to:
- Sites management
- Employee management  
- Attendance management
- Payroll viewing

### ✅ User Management (Superadmin Only)
- admin1 and admin2 should get 403 (Forbidden)
- Only superadmin has access

## Expected Results

```
Phase 2: Salary Codes Access Control
------------------------------------------------------------
✓ List salary codes (admin1): GET /salary-codes → 200
✓ List salary codes (admin2): GET /salary-codes → 200
✓ Create salary code (superadmin): POST /salary-codes → 201
✓ Create salary code (admin1): POST /salary-codes/create → 201
✓ Create salary code (should FAIL) (admin2): POST /salary-codes/create → 403
```

## Manual Testing Checklist

Beyond the automated tests, manually verify:

### Frontend Testing
- [ ] Login as admin1 - redirects to `/dashboard`
- [ ] Login as admin2 - redirects to `/dashboard`
- [ ] admin1 can see "Sites" in sidebar
- [ ] admin2 cannot see "Sites" in sidebar
- [ ] Both can see salary codes list
- [ ] admin1 can create/edit salary codes
- [ ] admin2 gets "403 Forbidden" when trying to create/edit salary codes

### Database Verification
```sql
-- Check user roles
SELECT id, name, email, username, role FROM users 
WHERE role IN ('admin', 'admin1', 'admin2', 'superadmin');

-- Check role constraint
SELECT conname, contype, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'users'::regclass AND conname LIKE '%role%';
```

## Troubleshooting

### "Could not log in all users"
- Make sure you've created users with admin1 and admin2 roles
- Update the credentials in the test script
- Verify the backend server is running

### "Connection refused"
- Make sure Flask backend is running on `http://localhost:5000`
- Check if the port is correct

### Tests fail with 401 Unauthorized
- Check if tokens are being generated correctly
- Verify user credentials are correct

### admin2 can create salary codes (should fail)
- Check if `routes/salary_codes.py` has correct role checks
- Verify the backend has been restarted after code changes

## Quick SQL Commands for Role Management

```sql
-- View all users and their roles
SELECT id, name, email, username, role, site_id 
FROM users 
ORDER BY role, name;

-- Promote user to admin1 (full access)
UPDATE users SET role = 'admin1' WHERE email = 'user@example.com';

-- Promote user to admin2 (restricted)
UPDATE users SET role = 'admin2' WHERE email = 'user@example.com';

-- Demote back to regular admin (if needed)
UPDATE users SET role = 'admin' WHERE email = 'user@example.com';
```
