#!/usr/bin/env python3
"""
Test script to verify bulk import functionality with user's actual data format
"""

import pandas as pd
import os
from flask import Flask
from models import db
from services.employee_service import bulk_import_from_frames
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def test_user_data_import():
    """Test the bulk import functionality with user's actual data format"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        # Create sample data matching user's format
        user_data = [
            {
                'Full Name': 'Zara Dash',
                'Date of Birth': '2004-11-07',
                'Gender': 'Female',
                'Marital Status': 'Married',
                'Nationality': 'Indian',
                'Blood Group': 'B-',
                'Permanent Address': 'H.No. 77, Dara Street, Ambattur 005469',
                'Mobile Number': '6423864884',
                'Alternate Contact Number': '6503334831',
                'Aadhaar Number': '790733525922',
                'PAN Card Number': 'WQTLS9128N',
                'Voter ID / Driving License': 'DL-4057622',
                'UAN': '382363272997',
                'ESIC Number': '9287770407',
                'Bank Account Number': '7716317736',
                'Bank Name': 'State Bank of India',
                'IFSC Code': 'GMAL0191877',
                'Salary Code': 'EMP6515',
                'Date of Joining': '2023-06-06',
                'Employment Type': 'Full-time',
                'Department': 'Marketing',
                'Designation': 'Coordinator',
                'Work Location': 'Tiruchirappalli',
                'Reporting Manager': 'Riya Cherian',
                'Skill Category': 'Management',
                'Salary Advance/Loan': '1536',
                'PF Applicability': 'No',
                'ESIC Applicability': 'No',
                'Professional Tax Applicability': 'No',
                'Experience Duration': '0',
                'Highest Qualification': 'B.Sc',
                'Year of Passing': '2021',
                'Additional Certifications': '',
                'Emergency Contact Name': 'Miraan Mane',
                'Emergency Relationship': 'Friend',
                'Emergency Phone Number': '7856569650'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(user_data)
        sheet_frames = {'Sheet1': df}
        
        print("Testing bulk import with user's actual data format...")
        print(f"Data contains {len(user_data)} employee(s)")
        print(f"Columns: {list(df.columns)}")
        
        try:
            result = bulk_import_from_frames(sheet_frames)
            
            print("\n✅ Bulk import test completed!")
            print(f"Inserted: {result['inserted']} employees")
            print(f"Errors: {len(result['errors'])}")
            
            if result['errors']:
                print("\nErrors encountered:")
                for error in result['errors']:
                    print(f"  Row {error['row_index'] + 1}: {error['error']}")
            else:
                print("🎉 All employees imported successfully!")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_user_data_import()
