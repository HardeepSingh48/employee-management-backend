#!/usr/bin/env python3
"""
Test script to verify pandas read_excel functionality
"""

import pandas as pd
from io import BytesIO

def test_pandas_excel():
    """Test if pandas can read Excel files"""
    
    print("Testing pandas read_excel functionality...")
    print("=" * 50)
    
    try:
        # Create a simple test DataFrame
        test_data = {
            'Employee ID': ['EMP001', 'EMP002', 'EMP003'],
            'Employee Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'Skill Level': ['Senior', 'Junior', 'Mid'],
            '01/08/2025': ['P', 'A', 'L'],
            '02/08/2025': ['P', 'P', 'P']
        }
        
        df = pd.DataFrame(test_data)
        print("✅ Created test DataFrame successfully")
        
        # Test writing to Excel
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        print("✅ Wrote DataFrame to Excel successfully")
        
        # Test reading from Excel
        df_read = pd.read_excel(excel_buffer, engine='openpyxl')
        print("✅ Read DataFrame from Excel successfully")
        
        print(f"✅ DataFrame shape: {df_read.shape}")
        print(f"✅ Columns: {list(df_read.columns)}")
        
        print("\n" + "=" * 50)
        print("✅ All pandas Excel tests passed!")
        print("The bulk attendance upload should now work properly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your pandas and openpyxl installation.")

if __name__ == "__main__":
    test_pandas_excel()
