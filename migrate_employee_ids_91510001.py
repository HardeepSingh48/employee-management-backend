from models import db
from sqlalchemy import text

def delete_all_employees():
    """
    Delete all existing employees - USE WITH CAUTION!
    """
    try:
        result = db.session.execute(text("SELECT COUNT(*) as count FROM employees")).fetchone()
        print(f"Found {result.count} employees to delete")
        
        if result.count > 0:
            confirm = input(f"Are you sure you want to delete ALL {result.count} employees? (type 'DELETE ALL' to confirm): ")
            if confirm != "DELETE ALL":
                print("Operation cancelled.")
                return False
        
        # Delete all employees
        db.session.execute(text("DELETE FROM employees"))
        db.session.commit()
        
        print("✓ All employees deleted")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to delete employees - {str(e)}")
        return False

def setup_fresh_sequence():
    """
    Set up a fresh sequence starting from 91510001
    """
    try:
        print("Setting up fresh employee ID sequence...")
        
        # Drop existing sequence if present
        db.session.execute(text("DROP SEQUENCE IF EXISTS employee_id_seq CASCADE"))
        
        # Create new sequence starting from 91510001
        db.session.execute(text("""
            CREATE SEQUENCE employee_id_seq 
            START WITH 91510001 
            INCREMENT BY 1
            OWNED BY employees.employee_id
        """))
        
        # Set as default for the table
        db.session.execute(text("""
            ALTER TABLE employees 
            ALTER COLUMN employee_id SET DEFAULT nextval('employee_id_seq')
        """))
        
        db.session.commit()
        
        print("✓ Sequence created successfully!")
        print("✓ Next employee will get ID: 91510001")
        
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Sequence setup failed - {str(e)}")
        return False

def verify_setup():
    """
    Verify the setup by checking sequence status
    """
    try:
        print("=== Verifying Setup ===")
        
        # Check employee count (should be 0)
        result = db.session.execute(text("SELECT COUNT(*) as count FROM employees")).fetchone()
        print(f"Total employees: {result.count}")
        
        # Check sequence - using the actual sequence object instead of information_schema
        seq_result = db.session.execute(text("SELECT nextval('employee_id_seq')")).fetchone()
        next_id = seq_result[0]
        
        # Reset the sequence back (since we just consumed a value)
        db.session.execute(text("SELECT setval('employee_id_seq', 91510001, false)"))
        db.session.commit()
        
        print(f"✓ Sequence ready - next employee will get ID: {next_id}")
        
        if next_id == 91510001:
            print("✓ Setup verification successful!")
            return True
        else:
            print(f"⚠ WARNING: Expected 91510001, got {next_id}")
            return False
        
    except Exception as e:
        print(f"ERROR: Verification failed - {str(e)}")
        return False

def test_employee_creation():
    """
    Test creating a new employee to verify the sequence works
    """
    try:
        print("\n=== Testing Employee Creation ===")
        
        # Create test employee
        result = db.session.execute(text("""
            INSERT INTO employees (first_name, last_name, employment_status)
            VALUES ('Test', 'Employee', 'Active')
            RETURNING employee_id
        """))
        
        new_id = result.fetchone()[0]
        print(f"✓ Test employee created with ID: {new_id}")
        
        if new_id == 91510001:
            print("✓ Perfect! New ID format is working correctly!")
        else:
            print(f"⚠ WARNING: Expected 91510001, got {new_id}")
        
        # Clean up the test employee
        db.session.execute(text("DELETE FROM employees WHERE employee_id = :id"), {"id": new_id})
        db.session.commit()
        print("✓ Test employee cleaned up")
        
        return new_id == 91510001
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Test failed - {str(e)}")
        return False

def fresh_start_setup():
    """
    Complete fresh start setup - deletes all employees and sets up new sequence
    """
    print("=== FRESH START SETUP ===")
    print("This will DELETE ALL existing employees and set up new sequence from 91510001")
    print()
    
    # Step 1: Delete all employees
    if not delete_all_employees():
        return False
    
    # Step 2: Set up fresh sequence
    if not setup_fresh_sequence():
        return False
    
    # Step 3: Verify setup
    if not verify_setup():
        return False
    
    # Step 4: Test (optional)
    test_choice = input("\nWould you like to test employee creation? (y/n): ").strip().lower()
    if test_choice == 'y':
        test_employee_creation()
    
    print("\n=== FRESH START COMPLETE! ===")
    print("✓ All old employees deleted")
    print("✓ New sequence ready starting from 91510001")
    print("✓ Your system is ready for new employees!")
    
    return True

def check_status():
    """
    Check current status
    """
    print("=== Current Status ===")
    
    try:
        # Employee count
        result = db.session.execute(text("SELECT COUNT(*) as count FROM employees")).fetchone()
        print(f"Total employees: {result.count}")
        
        if result.count > 0:
            # Show ID range if employees exist
            id_range = db.session.execute(text("""
                SELECT MIN(employee_id) as min_id, MAX(employee_id) as max_id 
                FROM employees
            """)).fetchone()
            print(f"ID range: {id_range.min_id} - {id_range.max_id}")
        
        # Check sequence status
        try:
            # Get current sequence value without consuming it
            current = db.session.execute(text("""
                SELECT last_value, is_called FROM employee_id_seq
            """)).fetchone()
            
            if current.is_called:
                next_id = current.last_value + 1
            else:
                next_id = current.last_value
                
            print(f"Next employee ID: {next_id}")
            
        except Exception as e:
            print(f"Sequence status: Not found - {str(e)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

# Quick helper functions
def fresh_start():
    """Quick fresh start function"""
    return fresh_start_setup()

def status():
    """Quick status function"""
    return check_status()

def preview_next_id():
    """Preview what the next employee ID will be"""
    try:
        result = db.session.execute(text("""
            SELECT last_value, is_called FROM employee_id_seq
        """)).fetchone()
        
        if result.is_called:
            next_id = result.last_value + 1
        else:
            next_id = result.last_value
            
        print(f"Next employee ID will be: {next_id}")
        return next_id
        
    except Exception as e:
        print(f"Could not get next ID: {str(e)}")
        return None