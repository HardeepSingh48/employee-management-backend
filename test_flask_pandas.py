#!/usr/bin/env python3
"""
Test pandas read_excel within Flask context
"""

from flask import Flask
import pandas as pd
from io import BytesIO

app = Flask(__name__)

def test_pandas_in_flask():
    """Test pandas read_excel in Flask context"""
    
    print("Testing pandas read_excel in Flask context...")
    print("=" * 50)
    
    try:
        # Create test data
        test_data = {
            'Employee ID': ['EMP001', 'EMP002'],
            'Employee Name': ['John Doe', 'Jane Smith'],
            '01/08/2025': ['P', 'A']
        }
        
        df = pd.DataFrame(test_data)
        print("✅ Created test DataFrame")
        
        # Write to Excel buffer
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        print("✅ Wrote to Excel buffer")
        
        # Try reading with explicit engine
        try:
            df_read = pd.read_excel(excel_buffer, engine='openpyxl')
            print("✅ Successfully read with openpyxl engine")
        except Exception as e:
            print(f"❌ Failed with openpyxl: {e}")
            
            # Try without engine specification
            try:
                excel_buffer.seek(0)
                df_read = pd.read_excel(excel_buffer)
                print("✅ Successfully read without engine specification")
            except Exception as e2:
                print(f"❌ Failed without engine: {e2}")
                
                # Try with xlrd engine
                try:
                    excel_buffer.seek(0)
                    df_read = pd.read_excel(excel_buffer, engine='xlrd')
                    print("✅ Successfully read with xlrd engine")
                except Exception as e3:
                    print(f"❌ Failed with xlrd: {e3}")
        
        print(f"✅ Final DataFrame shape: {df_read.shape}")
        
    except Exception as e:
        print(f"❌ General error: {e}")

if __name__ == "__main__":
    test_pandas_in_flask()
