# 🏗️ Backend Folder Structure Guide

## 🎯 Overview

The backend has been restructured using **Domain-Driven Design (DDD)** principles to improve organization, maintainability, and scalability.

## 🏗️ New Backend Structure

```
employee-management-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # Application factory
│   └── config.py                 # Configuration settings
├── domains/                      # Domain-driven organization
│   ├── auth/                     # Authentication domain
│   │   ├── models/
│   │   │   └── user.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   └── employee_dashboard.py
│   │   ├── services/
│   │   │   └── auth_service.py
│   │   └── schemas/
│   │       └── auth_schemas.py
│   ├── employees/                # Employee management domain
│   │   ├── models/
│   │   │   ├── employee.py
│   │   │   ├── department.py
│   │   │   └── account_details.py
│   │   ├── routes/
│   │   │   ├── employees.py
│   │   │   └── departments.py
│   │   ├── services/
│   │   │   └── employee_service.py
│   │   └── schemas/
│   │       └── employee_schemas.py
│   ├── attendance/               # Attendance management domain
│   │   ├── models/
│   │   │   ├── attendance.py
│   │   │   └── holiday.py
│   │   ├── routes/
│   │   │   └── attendance.py
│   │   ├── services/
│   │   │   └── attendance_service.py
│   │   └── schemas/
│   │       └── attendance_schemas.py
│   ├── salary/                   # Salary management domain
│   │   ├── models/
│   │   │   └── wage_master.py
│   │   ├── routes/
│   │   │   ├── salary_codes.py
│   │   │   └── salary.py
│   │   ├── services/
│   │   │   ├── salary_service.py
│   │   │   └── wage_master_service.py
│   │   └── schemas/
│   │       └── salary_schemas.py
│   └── shared/                   # Shared across domains
│       ├── models/
│       │   └── base.py
│       ├── services/
│       │   └── base_service.py
│       ├── utils/
│       │   ├── validators.py
│       │   ├── excel_parser.py
│       │   └── upload.py
│       └── middleware/
│           └── auth_middleware.py
├── database/
│   ├── __init__.py
│   ├── connection.py
│   └── migrations/
├── tests/
│   ├── unit/
│   │   ├── test_auth/
│   │   ├── test_employees/
│   │   ├── test_attendance/
│   │   └── test_salary/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── create_test_users.py
│   ├── init_db.py
│   └── migrate_db.py
├── uploads/                      # File uploads
├── requirements.txt
└── main.py                       # Application entry point
```

## 🎯 Domain Organization

### **Auth Domain**
- User authentication and authorization
- JWT token management
- Employee dashboard access
- Role-based permissions

### **Employees Domain**
- Employee registration and management
- Department management
- Account details
- Employee profiles

### **Attendance Domain**
- Attendance marking and tracking
- Holiday management
- Attendance reports
- Time tracking

### **Salary Domain**
- Salary code management
- Wage calculations
- Payroll processing
- Salary reports

### **Shared Domain**
- Common utilities and helpers
- Base models and services
- Validation functions
- File upload handling

## 🔧 Benefits

### **1. Domain Separation**
- Clear business domain boundaries
- Easier to understand and maintain
- Better team collaboration

### **2. Scalability**
- Easy to add new domains
- Independent domain development
- Microservices-ready architecture

### **3. Maintainability**
- Related code is co-located
- Clear dependency management
- Easier testing and debugging

### **4. Code Reusability**
- Shared utilities and services
- Common patterns across domains
- Consistent error handling

## 📋 Migration Status

### **✅ Started**
- Created domain folder structure
- Moved auth-related files
- Moved employee-related models
- Created documentation

### **🔄 Next Steps**
- Complete file migration
- Update import paths
- Create domain-specific services
- Add comprehensive tests
- Update deployment scripts

## 🚀 Usage Guidelines

### **Adding New Features**
1. Identify the appropriate domain
2. Create files in the domain structure
3. Follow naming conventions
4. Add tests for new functionality

### **Cross-Domain Communication**
- Use shared services for common functionality
- Avoid direct model imports between domains
- Use events or services for domain communication

This improved structure provides a solid foundation for scaling the backend and makes it much easier to maintain and extend the Employee Management System.
