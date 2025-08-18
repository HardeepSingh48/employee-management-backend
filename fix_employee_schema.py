#!/usr/bin/env python3
"""
Fix Employee Schema - Add missing father_name column
"""

import psycopg2
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

def fix_employee_schema():
    """Add missing father_name column to employees table"""
    print("🔧 Fixing Employee Schema - Adding missing columns")
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
        
        print("📋 Checking employees table schema...")
        
        # Check if father_name column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'employees' AND column_name = 'father_name'
        """)
        
        if not cursor.fetchone():
            print("➕ Adding missing 'father_name' column to employees table...")
            cursor.execute("ALTER TABLE employees ADD COLUMN father_name VARCHAR(100)")
            conn.commit()
            print("✅ Added father_name column")
        else:
            print("✅ father_name column already exists")
        
        # Check and add all potentially missing columns from Employee model
        missing_columns = [
            ("place_of_birth", "VARCHAR(100)"),
            ("job_title", "VARCHAR(100)"),
            ("family_details", "VARCHAR(500)"),
            ("gender", "VARCHAR(20)"),
            ("nationality", "VARCHAR(50) DEFAULT 'Indian'"),
            ("blood_group", "VARCHAR(5)"),
            ("alternate_contact_number", "VARCHAR(20)"),
            ("pan_card_number", "VARCHAR(15)"),
            ("voter_id_driving_license", "VARCHAR(50)"),
            ("uan", "VARCHAR(20)"),
            ("esic_number", "VARCHAR(20)"),
            ("employment_type", "VARCHAR(50)"),
            ("designation", "VARCHAR(100)"),
            ("work_location", "VARCHAR(100)"),
            ("reporting_manager", "VARCHAR(100)"),
            ("base_salary", "FLOAT"),
            ("skill_category", "VARCHAR(100)"),
            ("wage_rate", "FLOAT"),
            ("pf_applicability", "BOOLEAN DEFAULT FALSE"),
            ("esic_applicability", "BOOLEAN DEFAULT FALSE"),
            ("professional_tax_applicability", "BOOLEAN DEFAULT FALSE"),
            ("salary_advance_loan", "VARCHAR(200)"),
            ("highest_qualification", "VARCHAR(100)"),
            ("year_of_passing", "VARCHAR(10)"),
            ("additional_certifications", "VARCHAR(500)"),
            ("experience_duration", "VARCHAR(50)"),
            ("emergency_contact_name", "VARCHAR(100)"),
            ("emergency_contact_relationship", "VARCHAR(50)"),
            ("emergency_contact_phone", "VARCHAR(20)"),
            ("salary_code", "VARCHAR(50)"),
            ("created_date", "DATE DEFAULT CURRENT_DATE"),
            ("created_by", "VARCHAR(100)"),
            ("updated_date", "DATE"),
            ("updated_by", "VARCHAR(100)"),
        ]
        
        for column_name, column_type in missing_columns:
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'employees' AND column_name = '{column_name}'
            """)
            
            if not cursor.fetchone():
                print(f"➕ Adding missing '{column_name}' column...")
                cursor.execute(f"ALTER TABLE employees ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"✅ Added {column_name} column")
            else:
                print(f"✅ {column_name} column already exists")
        
        # Add constraints if they don't exist
        print("\n🔧 Adding constraints...")

        # Employment status constraint
        try:
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.check_constraints
                        WHERE constraint_name LIKE '%employment_status%'
                    ) THEN
                        ALTER TABLE employees
                        ADD CONSTRAINT check_employment_status
                        CHECK (employment_status IN ('Active', 'Inactive', 'On Leave'));
                    END IF;
                END $$;
            """)
            conn.commit()
            print("✅ Added employment_status constraint")
        except Exception as e:
            print(f"⚠️  Warning: Could not add employment_status constraint: {e}")

        # Marital status constraint
        try:
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.check_constraints
                        WHERE constraint_name LIKE '%marital_status%'
                    ) THEN
                        ALTER TABLE employees
                        ADD CONSTRAINT check_marital_status
                        CHECK (marital_status IN ('unmarried', 'married'));
                    END IF;
                END $$;
            """)
            conn.commit()
            print("✅ Added marital_status constraint")
        except Exception as e:
            print(f"⚠️  Warning: Could not add marital_status constraint: {e}")

        # Verify the fix
        print("\n🔍 Verifying employees table...")
        cursor.execute("SELECT COUNT(*) FROM employees")
        count = cursor.fetchone()[0]
        print(f"✅ Employees table accessible - {count} records found")

        # Test a query that includes multiple columns
        try:
            cursor.execute("SELECT employee_id, first_name, last_name, father_name, place_of_birth FROM employees LIMIT 1")
            print("✅ All new columns are accessible")
        except Exception as e:
            print(f"❌ Error accessing new columns: {e}")
            return False
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎉 Employee schema fix completed successfully!")
        print("\n📋 Next steps:")
        print("1. Run: python create_test_users.py")
        print("2. Start the server: python app.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing employee schema: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your database connection in config.py")
        print("2. Ensure PostgreSQL is running")
        print("3. Verify database credentials")
        return False

if __name__ == "__main__":
    fix_employee_schema()
