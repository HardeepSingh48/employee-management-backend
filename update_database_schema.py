#!/usr/bin/env python3
"""
Database schema update script to add missing columns for attendance system
"""

import psycopg2
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

def update_database_schema():
    """Add missing columns to existing tables"""
    
    # Database connection
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting database schema update...")
        
        # 1. Add employment_status column to employees table if it doesn't exist
        print("📝 Adding employment_status column to employees table...")
        cursor.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'employees' AND column_name = 'employment_status'
                ) THEN
                    ALTER TABLE employees 
                    ADD COLUMN employment_status VARCHAR(20) DEFAULT 'Active';
                    
                    ALTER TABLE employees 
                    ADD CONSTRAINT check_employment_status 
                    CHECK (employment_status IN ('Active', 'Inactive', 'On Leave'));
                    
                    RAISE NOTICE 'Added employment_status column to employees table';
                ELSE
                    RAISE NOTICE 'employment_status column already exists in employees table';
                END IF;
            END $$;
        """)
        
        # 2. Create holidays table if it doesn't exist
        print("📝 Creating holidays table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holidays (
                holiday_id VARCHAR(50) PRIMARY KEY,
                holiday_name VARCHAR(100) NOT NULL,
                holiday_date DATE NOT NULL UNIQUE,
                holiday_type VARCHAR(20) NOT NULL DEFAULT 'Company',
                description TEXT,
                is_paid BOOLEAN DEFAULT TRUE,
                is_mandatory BOOLEAN DEFAULT TRUE,
                is_active BOOLEAN DEFAULT TRUE,
                applicable_departments TEXT,
                applicable_locations TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_date TIMESTAMP,
                updated_by VARCHAR(100),
                CONSTRAINT check_holiday_type 
                CHECK (holiday_type IN ('National', 'Regional', 'Company', 'Optional'))
            );
        """)
        print("✅ Holidays table created/verified")
        
        # 3. Update attendance table structure
        print("📝 Updating attendance table structure...")
        
        # Check if attendance table exists, if not create it
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id VARCHAR(50) PRIMARY KEY,
                employee_id VARCHAR(50) NOT NULL,
                attendance_date DATE NOT NULL,
                check_in_time TIMESTAMP,
                check_out_time TIMESTAMP,
                attendance_status VARCHAR(20) NOT NULL DEFAULT 'Present',
                overtime_hours FLOAT DEFAULT 0.0,
                late_minutes INTEGER DEFAULT 0,
                early_departure_minutes INTEGER DEFAULT 0,
                total_hours_worked FLOAT DEFAULT 8.0,
                is_holiday BOOLEAN DEFAULT FALSE,
                is_weekend BOOLEAN DEFAULT FALSE,
                remarks TEXT,
                marked_by VARCHAR(20) DEFAULT 'employee',
                is_approved BOOLEAN DEFAULT TRUE,
                approved_by VARCHAR(100),
                approved_date TIMESTAMP,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                updated_date TIMESTAMP,
                updated_by VARCHAR(100),
                CONSTRAINT fk_attendance_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                CONSTRAINT check_attendance_status 
                CHECK (attendance_status IN ('Present', 'Absent', 'Late', 'Half Day', 'Holiday', 'Leave')),
                CONSTRAINT unique_employee_date_attendance 
                UNIQUE (employee_id, attendance_date)
            );
        """)
        print("✅ Attendance table created/verified")
        
        # 4. Add any missing columns to attendance table
        attendance_columns = [
            ("overtime_hours", "FLOAT DEFAULT 0.0"),
            ("late_minutes", "INTEGER DEFAULT 0"),
            ("early_departure_minutes", "INTEGER DEFAULT 0"),
            ("total_hours_worked", "FLOAT DEFAULT 8.0"),
            ("is_holiday", "BOOLEAN DEFAULT FALSE"),
            ("is_weekend", "BOOLEAN DEFAULT FALSE"),
            ("remarks", "TEXT"),
            ("marked_by", "VARCHAR(20) DEFAULT 'employee'"),
            ("is_approved", "BOOLEAN DEFAULT TRUE"),
            ("approved_by", "VARCHAR(100)"),
            ("approved_date", "TIMESTAMP")
        ]
        
        for column_name, column_definition in attendance_columns:
            cursor.execute(f"""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'attendance' AND column_name = '{column_name}'
                    ) THEN
                        ALTER TABLE attendance ADD COLUMN {column_name} {column_definition};
                        RAISE NOTICE 'Added {column_name} column to attendance table';
                    END IF;
                END $$;
            """)
        
        # 5. Update attendance status constraint if needed
        cursor.execute("""
            DO $$ 
            BEGIN 
                -- Drop old constraint if exists
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE table_name = 'attendance' AND constraint_name = 'attendance_attendance_status_check'
                ) THEN
                    ALTER TABLE attendance DROP CONSTRAINT attendance_attendance_status_check;
                END IF;
                
                -- Add new constraint
                ALTER TABLE attendance 
                ADD CONSTRAINT check_attendance_status_new 
                CHECK (attendance_status IN ('Present', 'Absent', 'Late', 'Half Day', 'Holiday', 'Leave'));
                
                RAISE NOTICE 'Updated attendance status constraint';
            EXCEPTION 
                WHEN duplicate_object THEN 
                    RAISE NOTICE 'Attendance status constraint already exists';
            END $$;
        """)
        
        # Commit all changes
        conn.commit()
        print("✅ Database schema update completed successfully!")
        
        # Show table info
        print("\n📊 Current table structures:")
        
        # Show employees table columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'employees' 
            ORDER BY ordinal_position;
        """)
        print("\n👥 Employees table columns:")
        for row in cursor.fetchall():
            print(f"  - {row[0]} ({row[1]}) - Nullable: {row[2]} - Default: {row[3]}")
        
        # Show attendance table columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'attendance' 
            ORDER BY ordinal_position;
        """)
        print("\n📅 Attendance table columns:")
        for row in cursor.fetchall():
            print(f"  - {row[0]} ({row[1]}) - Nullable: {row[2]} - Default: {row[3]}")
        
        # Show holidays table columns
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'holidays' 
            ORDER BY ordinal_position;
        """)
        print("\n🎉 Holidays table columns:")
        for row in cursor.fetchall():
            print(f"  - {row[0]} ({row[1]}) - Nullable: {row[2]} - Default: {row[3]}")
        
    except Exception as e:
        print(f"❌ Error updating database schema: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_database_schema()
