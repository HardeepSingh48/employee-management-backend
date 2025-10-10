# Employee Management System - Fresh Database Setup Guide

## Overview

This guide explains how to set up the Employee Management System database on a fresh VPS server **without importing data from Supabase**. The new `init_fresh_db.py` script provides a single-command initialization similar to Prisma, automatically creating all tables, constraints, indexes, sequences, and seed data.

## Quick Start

### Prerequisites
```bash
# Install PostgreSQL 15 on your VPS
sudo apt update && sudo apt upgrade -y
sudo apt install postgresql-15 postgresql-contrib-15 -y

# Create database and user
sudo -u postgres psql
CREATE DATABASE employee_management;
CREATE USER app_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE employee_management TO app_user;
ALTER USER app_user CREATEDB;
\q
```

### Single-Command Setup
```bash
# Set your database URL
export DATABASE_URL="postgresql://app_user:your_secure_password@localhost:5432/employee_management"

# Run the initialization script
cd employee-management-backend
python init_fresh_db.py --seed-demo
```

That's it! Your database is now fully set up and ready to use.

## What Gets Created

### 🏗️ Database Schema
- **All Tables**: employees, attendance, users, departments, holidays, wage_masters, deductions, sites
- **Relationships**: Foreign keys, constraints, and proper table relationships
- **Constraints**: Attendance status limited to Present/Absent/OFF only

### 🔢 Sequences
- **Employee ID Sequence**: Automatically starts from 91510001
- **Auto-increment**: New employees get sequential IDs starting from 91510001

### ⚡ Performance Indexes
- **Attendance Indexes**: Optimized for date-based queries and employee lookups
- **Employee Indexes**: Fast searches by phone, email, department, etc.
- **Composite Indexes**: Multi-column indexes for complex queries

### 🌱 Seed Data
- **Departments**: 10 default departments (HR, IT, Finance, etc.)
- **Holidays**: Current year holidays (New Year, Independence Day, etc.)
- **Demo Users** (optional):
  - Admin: `admin@company.com` / `admin123`
  - Employee: `employee@company.com` / `emp123` (ID: 91510001)

## Command Options

```bash
# Basic setup (tables, constraints, indexes, sequences, essential data)
python init_fresh_db.py

# Full setup with demo users
python init_fresh_db.py --seed-demo

# Drop everything and recreate from scratch
python init_fresh_db.py --drop --seed-demo

# Check current database status
python init_fresh_db.py --status

# Fast setup without verification (not recommended)
python init_fresh_db.py --no-verify
```

## Migration Changes Included

### ✅ Database Constraints
- **Attendance Status Constraint**: Only allows 'Present', 'Absent', and 'OFF' values
- **Foreign Key Constraints**: Proper relationships between all tables
- **Data Integrity**: Prevents invalid data entry

### ✅ Employee ID Sequence
- **Starting Value**: 91510001 (as requested)
- **Auto-increment**: Each new employee gets the next sequential ID
- **No Gaps**: Continuous numbering from the starting value

### ✅ Performance Optimizations
- **Query Indexes**: Optimized for salary calculations and attendance reports
- **Bulk Operations**: Efficient handling of large datasets
- **Connection Pooling**: Configured for high-performance operations

### ✅ System Simplifications
- **Attendance Status**: Simplified to Present/Absent/OFF only
- **Late Days**: Converted to Present (no separate tracking)
- **Half Days**: Converted to Absent (simplified logic)

## Verification

After setup, verify everything works:

```bash
# Check database status
python init_fresh_db.py --status

# Test salary calculation
python -c "
from app import create_app
from services.salary_service import SalaryService
app = create_app()
with app.app_context():
    result = SalaryService.generate_monthly_salary_data(2024, 10)
    print('✅ Salary calculation works!' if result['success'] else '❌ Salary calculation failed')
"

# Test attendance report
python -c "
from app import create_app
from services.attendance_service import AttendanceService
app = create_app()
with app.app_context():
    result = AttendanceService.get_monthly_attendance_report('DEMO_SITE', '2024-10-01', '2024-10-31')
    print('✅ Attendance report works!' if result['success'] else '❌ Attendance report failed')
"
```

## Application Configuration

### Environment Variables
```bash
# .env file
DATABASE_URL=postgresql://app_user:your_secure_password@localhost:5432/employee_management
SQLALCHEMY_DATABASE_URI=postgresql://app_user:your_secure_password@localhost:5432/employee_management
FLASK_ENV=production
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret
```

### Docker Setup (Optional)
```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: employee_management
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: your_secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  app:
    build: .
    environment:
      - DATABASE_URL=postgresql://app_user:your_secure_password@db:5432/employee_management
    depends_on:
      - db
    ports:
      - "5000:5000"
    restart: unless-stopped

volumes:
  postgres_data:
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Fix PostgreSQL permissions
sudo -u postgres psql -d employee_management
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
\q
```

#### 2. Sequence Not Working
```bash
# Reset sequence manually
sudo -u postgres psql -d employee_management
SELECT setval('employee_id_seq', 91510001, false);
\q
```

#### 3. Connection Issues
```bash
# Test database connection
python -c "
from app import create_app
app = create_app(register_blueprints=False)
with app.app_context():
    from models import db
    db.session.execute('SELECT 1')
    print('✅ Database connection OK')
"
```

#### 4. Missing Tables
```bash
# Recreate tables
python init_fresh_db.py --drop
```

## Advanced Configuration

### Custom Employee ID Starting Value
Edit `init_fresh_db.py` and change:
```python
START_VALUE = 91510001  # Change this value
```

### Additional Departments
Add to the `departments_data` list in `init_fresh_db.py`:
```python
{"department_id": "NEW_DEPT", "department_name": "New Department", "description": "Description here"}
```

### Custom Holidays
Modify the `holidays_data` list in `init_fresh_db.py` with your local holidays.

## Migration from Supabase

If you need to migrate existing data from Supabase:

1. **Export from Supabase** (see POSTGRESQL_MIGRATION_GUIDE.md)
2. **Setup fresh database** using this script
3. **Import data** using pg_restore
4. **Run data migration scripts** if needed

```bash
# After fresh setup, import your data
pg_restore --dbname=employee_management --username=app_user /path/to/supabase_backup.dump
```

## Security Best Practices

### Database Security
```bash
# Configure pg_hba.conf for secure access
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Add your app server IP only
host    employee_management    app_user    [YOUR_APP_IP]/32    md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Backup Strategy
```bash
# Daily automated backups
sudo nano /usr/local/bin/db_backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U app_user -h localhost employee_management > /backups/db_$DATE.sql

# Add to crontab
0 2 * * * /usr/local/bin/db_backup.sh
```

## Performance Monitoring

### Key Metrics to Monitor
- **Connection Count**: `SELECT count(*) FROM pg_stat_activity;`
- **Slow Queries**: Check `pg_stat_statements` extension
- **Index Usage**: Monitor `pg_stat_user_indexes`
- **Table Sizes**: `SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables;`

## Support

If you encounter issues:

1. Check the database logs: `sudo tail -f /var/log/postgresql/postgresql-15-main.log`
2. Run status check: `python init_fresh_db.py --status`
3. Verify environment variables
4. Test with the demo data first

## Summary

The `init_fresh_db.py` script provides a **Prisma-like experience** for database initialization:

- ✅ **Single Command**: Complete setup with one command
- ✅ **All Constraints**: Includes all database constraints and migrations
- ✅ **Employee ID Sequence**: Starts from 91510001 as requested
- ✅ **Performance Optimized**: Includes all necessary indexes
- ✅ **Seed Data**: Essential departments and holidays included
- ✅ **Demo Users**: Optional demo accounts for testing
- ✅ **Verification**: Built-in checks to ensure everything works

Your Employee Management System is now ready for production use! 🚀