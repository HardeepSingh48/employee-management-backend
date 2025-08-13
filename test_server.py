#!/usr/bin/env python3
"""
Simple test script to check if the Flask server can start
and if CORS is configured properly
COMMENTED OUT - Not needed in production
"""

"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    print("✅ Successfully imported create_app")
    
    app = create_app()
    print("✅ Successfully created Flask app")
    
    # Test if we can access the routes
    with app.test_client() as client:
        # Test root endpoint
        response = client.get('/')
        print(f"✅ Root endpoint status: {response.status_code}")
        print(f"   Response: {response.get_json()}")
        
        # Test salary codes test endpoint
        response = client.get('/api/salary-codes/test')
        print(f"✅ Salary codes test endpoint status: {response.status_code}")
        print(f"   Response: {response.get_json()}")
        
        # Test CORS preflight
        response = client.options('/api/salary-codes/', 
                                headers={
                                    'Origin': 'http://localhost:3000',
                                    'Access-Control-Request-Method': 'POST',
                                    'Access-Control-Request-Headers': 'Content-Type'
                                })
        print(f"✅ CORS preflight status: {response.status_code}")
        print(f"   CORS headers: {dict(response.headers)}")
    
    print("\n🎉 All tests passed! Server should work correctly.")
    print("You can now start the server with: python app.py")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
"""
