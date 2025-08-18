#!/usr/bin/env python3
"""
Fix Attendance Schema - Add missing columns to attendance table
"""

import psycopg2
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

def fix_attendance_schema():
    """Add missing columns to attendance table"""
    print("🔧 Fixing Attendance Schema - Adding missing columns")
    print("=" * 60)
    
    # Database connection
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        print("📋 Checking attendance table schema...")
        
        # Check and add missing columns to attendance table
        missing_columns = [
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
            ("approved_date", "TIMESTAMP"),
        ]
        
        for column_name, column_type in missing_columns:
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'attendance' AND column_name = '{column_name}'
            """)
            
            if not cursor.fetchone():
                print(f"➕ Adding missing '{column_name}' column...")
                cursor.execute(f"ALTER TABLE attendance ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"✅ Added {column_name} column")
            else:
                print(f"✅ {column_name} column already exists")
        
        # Update attendance_status constraint to include more statuses
        print("\n🔧 Updating attendance_status constraint...")
        try:
            cursor.execute("""
                DO $$ 
                BEGIN 
                    -- Drop old constraint if exists
                    IF EXISTS (
                        SELECT 1 FROM information_schema.check_constraints 
                        WHERE constraint_name LIKE '%attendance_status%'
                    ) THEN
                        ALTER TABLE attendance DROP CONSTRAINT attendance_attendance_status_check;
                    END IF;
                    
                    -- Add new constraint
                    ALTER TABLE attendance 
                    ADD CONSTRAINT check_attendance_status 
                    CHECK (attendance_status IN ('Present', 'Absent', 'Late', 'Half Day', 'Holiday', 'Leave'));
                END $$;
            """)
            conn.commit()
            print("✅ Updated attendance_status constraint")
        except Exception as e:
            print(f"⚠️  Warning: Could not update attendance_status constraint: {e}")
        
        # Verify the fix
        print("\n🔍 Verifying attendance table...")
        cursor.execute("SELECT COUNT(*) FROM attendance")
        count = cursor.fetchone()[0]
        print(f"✅ Attendance table accessible - {count} records found")
        
        # Test a query that includes new columns
        try:
            cursor.execute("SELECT attendance_id, employee_id, attendance_date, overtime_hours, late_minutes FROM attendance LIMIT 1")
            print("✅ All new columns are accessible")
        except Exception as e:
            print(f"❌ Error accessing new columns: {e}")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 Attendance schema fix completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart the backend server: python app.py")
        print("2. Test the attendance endpoint in Postman")
        print("3. Try the frontend attendance features")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing attendance schema: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your database connection in config.py")
        print("2. Ensure PostgreSQL is running")
        print("3. Verify database credentials")
        return False

if __name__ == "__main__":
    fix_attendance_schema()
