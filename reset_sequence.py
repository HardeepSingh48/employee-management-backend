#!/usr/bin/env python3
"""
Simple script to reset employee ID sequence to start from 91510001
"""

from app import create_app
from models import db
from sqlalchemy import text
import os

# Set environment
os.environ['FLASK_ENV'] = 'development'
os.environ['CREATE_APP_ON_IMPORT'] = '0'  # Prevent auto-creation of app

def reset_sequence():
    """Reset the employee ID sequence appropriately based on existing data"""
    try:
        print("Resetting employee ID sequence...")

        # Check current sequence value
        result = db.session.execute(text('SELECT last_value FROM employee_id_seq')).fetchone()
        print(f'Current sequence last_value: {result[0]}')

        # Check if there are any employees
        count_result = db.session.execute(text('SELECT COUNT(*) as count FROM employees')).fetchone()
        employee_count = count_result.count
        print(f'Current employee count: {employee_count}')

        if employee_count > 0:
            # Find the maximum employee_id
            max_result = db.session.execute(text('SELECT MAX(employee_id) as max_id FROM employees')).fetchone()
            max_id = max_result.max_id
            print(f'Maximum employee_id: {max_id}')

            # Set sequence to max_id + 1
            new_start = max_id + 1
            db.session.execute(text('SELECT setval(\'employee_id_seq\', :start_val, false)'), {'start_val': new_start})
            db.session.commit()

            print(f'SUCCESS: Sequence reset to start from {new_start} (after existing max ID)')
            print(f'Next employee ID will be: {new_start}')
        else:
            # No employees, start from 91510000
            db.session.execute(text('SELECT setval(\'employee_id_seq\', 91510000, false)'))
            db.session.commit()

            print('SUCCESS: Sequence reset to start from 91510000 (no existing employees)')
            print('Next employee ID will be: 91510000')

        # Verify
        result = db.session.execute(text('SELECT last_value FROM employee_id_seq')).fetchone()
        print(f'After reset, last_value: {result[0]}')

        return True

    except Exception as e:
        print(f'Error: {e}')
        db.session.rollback()
        return False

if __name__ == '__main__':
    # Create Flask app without registering blueprints (for scripts)
    app = create_app(register_blueprints=False)

    with app.app_context():
        success = reset_sequence()
        if success:
            print("\nSUCCESS: Employee ID sequence has been reset!")
            # The next ID is already printed in the reset_sequence function
        else:
            print("\nFAILED: Could not reset sequence")