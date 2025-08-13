#!/usr/bin/env python3
"""
Test script to verify bulk import functionality
"""

import pandas as pd
import os
from flask import Flask
from models import db
from services.employee_service import bulk_import_from_frames
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

def test_bulk_import():
    """Test the bulk import functionality with sample data"""
    
    # Create Flask app for database operations
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["SECRET_KEY"] = SECRET_KEY
    
    db.init_app(app)
    
    with app.app_context():
        # Create sample data matching the Excel template
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
            },
            {
                'Full Name': 'Jane Smith',
                'Date of Birth': '1992-05-20',
                'Gender': 'Female',
                'Marital Status': 'Married',
                'Nationality': 'Indian',
                'Blood Group': 'A+',
                'Permanent Address': '456 Park Avenue, Mumbai',
                'Mobile Number': '9876543213',
                'Alternate Contact Number': '',
                'Aadhaar Number': '123456789013',
                'PAN Card Number': 'FGHIJ5678K',
                'Voter ID / Driving License': 'DL987654321',
                'UAN': '',
                'ESIC Number': '',
                'Date of Joining': '2023-02-01',
                'Employment Type': 'Full-time',
                'Department': 'HR',
                'Designation': 'HR Manager',
                'Work Location': 'Mumbai Office',
                'Reporting Manager': 'Director HR',
                'Salary Code': 'MUMMANAGERMAH',
                'Skill Category': 'Highly Skilled',
                'PF Applicability': 'TRUE',
                'ESIC Applicability': 'FALSE',
                'Professional Tax Applicability': 'TRUE',
                'Salary Advance/Loan': '5000',
                'Bank Account Number': '9876543210987654',
                'Bank Name': 'HDFC Bank',
                'IFSC Code': 'HDFC0001234',
                'Highest Qualification': "Master's",
                'Year of Passing': '2014',
                'Additional Certifications': 'SHRM Certified',
                'Experience Duration': '8',
                'Emergency Contact Name': 'Spouse Name',
                'Emergency Relationship': 'Spouse',
                'Emergency Phone Number': '9876543214'
            }
        ]
        
        # Create DataFrame
        df = pd.DataFrame(sample_data)
        sheet_frames = {'Employee Data': df}
        
        print("Testing bulk import with sample data...")
        print(f"Sample data contains {len(sample_data)} employees")
        
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

if __name__ == "__main__":
    test_bulk_import()
