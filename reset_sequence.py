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
    """Reset the employee ID sequence to start from 91510001"""
    try:
        print("Resetting employee ID sequence...")

        # Check current sequence value
        result = db.session.execute(text('SELECT last_value FROM employee_id_seq')).fetchone()
        print(f'Current sequence last_value: {result[0]}')

        # Reset sequence to start from 91510000 (so nextval will give 91510001)
        db.session.execute(text('SELECT setval(\'employee_id_seq\', 91510000, false)'))
        db.session.commit()

        # Verify
        result = db.session.execute(text('SELECT last_value FROM employee_id_seq')).fetchone()
        print(f'After reset, last_value: {result[0]}')

        # Reset the sequence back since we just consumed a value
        db.session.execute(text('SELECT setval(\'employee_id_seq\', 91510000, false)'))
        db.session.commit()

        print('SUCCESS: Sequence reset successfully!')
        print('Next employee ID will be: 91510001')
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
            print("Next employee will get ID: 91510001")
        else:
            print("\nFAILED: Could not reset sequence")