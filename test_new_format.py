#!/usr/bin/env python3
"""
Test script to verify the new Excel format works correctly
"""

import pandas as pd
from flask import Flask
from models import db
from utils.excel_parser import load_excel_to_frames, detect_excel_format
from services.employee_service import bulk_import_from_frames
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
import io

def test_new_format():
    """Test the new Excel format"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        # Create sample data matching the new Excel template format
        sample_data = [
            {
                'Full Name': 'John Doe',
                'Date of Birth': '1990-01-15',
                'Gender': 'Male',
                'Marital Status': 'Single',
                'Nationality': 'Indian',
                'Blood Group': 'O+',
                'Permanent Address': '123 Main Street, Delhi',
                'Mobile Number': '9876543210',
                'Alternate Contact Number': '9876543211',
                'Aadhaar Number': '123456789012',
                'PAN Card Number': 'ABCDE1234F',
                'Voter ID / Driving License': 'DL123456789',
                'UAN': '123456789012',
                'ESIC Number': '1234567890',
                'Date of Joining': '2023-01-01',
                'Employment Type': 'Full-time',
                'Department': 'IT',
                'Designation': 'Software Engineer',
                'Work Location': 'Delhi Office',
                'Reporting Manager': 'Manager Name',
                'Salary Code': 'DELENGINEERDELHI',
                'Skill Category': 'Skilled',
                'PF Applicability': 'TRUE',
                'ESIC Applicability': 'TRUE',
                'Professional Tax Applicability': 'FALSE',
                'Salary Advance/Loan': '0',
                'Bank Account Number': '1234567890123456',
                'Bank Name': 'State Bank of India',
                'IFSC Code': 'SBIN0001234',
                'Highest Qualification': "Bachelor's",
                'Year of Passing': '2012',
                'Additional Certifications': 'AWS Certified',
                'Experience Duration': '5',
                'Emergency Contact Name': 'Emergency Contact',
                'Emergency Relationship': 'Father',
                'Emergency Phone Number': '9876543212'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        
        print("Testing new Excel format...")
        print(f"Columns: {list(df.columns)}")
        
        # Test format detection
        format_type = detect_excel_format(df)
        print(f"Detected format: {format_type}")
        
        # Test Excel parsing (simulate file upload)
        sheet_frames = {'Sheet1': df}
        
        try:
            # Test bulk import
            result = bulk_import_from_frames(sheet_frames)
            
            print("\n✅ New format test completed!")
            print(f"Inserted: {result['inserted']} employees")
            print(f"Errors: {len(result['errors'])}")
            
            if result['errors']:
                print("\nErrors encountered:")
                for error in result['errors']:
                    print(f"  Row {error['row_index'] + 1}: {error['error']}")
            else:
                print("🎉 All employees imported successfully with new format!")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()

def test_missing_salary_code():
    """Test what happens when salary code is missing"""
    print("\n" + "="*50)
    print("Testing missing salary code scenario...")
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        # Create sample data WITHOUT salary code
        sample_data = [
            {
                'Full Name': 'Jane Smith',
                'Date of Birth': '1992-05-20',
                'Gender': 'Female',
                'Marital Status': 'Married',
                'Nationality': 'Indian',
                'Blood Group': 'A+',
                'Permanent Address': '456 Park Avenue, Mumbai',
                'Mobile Number': '9876543213',
                'Aadhaar Number': '123456789013',
                'PAN Card Number': 'FGHIJ5678K',
                'Date of Joining': '2023-02-01',
                'Employment Type': 'Full-time',
                'Department': 'HR',
                'Designation': 'HR Manager',
                'Work Location': 'Mumbai Office',
                # 'Salary Code': '',  # Missing salary code
                'Bank Account Number': '9876543210987654',
                'Bank Name': 'HDFC Bank',
                'IFSC Code': 'HDFC0001234',
                'Highest Qualification': "Master's",
                'Year of Passing': '2014',
                'Experience Duration': '8',
                'Emergency Contact Name': 'Spouse Name',
                'Emergency Relationship': 'Spouse',
                'Emergency Phone Number': '9876543214'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        sheet_frames = {'Sheet1': df}
        
        try:
            result = bulk_import_from_frames(sheet_frames)
            
            print(f"Inserted: {result['inserted']} employees")
            print(f"Errors: {len(result['errors'])}")
            
            if result['errors']:
                print("Expected errors for missing salary code:")
                for error in result['errors']:
                    print(f"  Row {error['row_index'] + 1}: {error['error']}")
                    
        except Exception as e:
            print(f"Exception (expected): {e}")

if __name__ == "__main__":
    test_new_format()
    test_missing_salary_code()
