#!/usr/bin/env python3
"""
Enhanced startup script with debugging and error handling
"""
import os
import sys
from datetime import datetime

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("📦 Checking Dependencies...")
    
    required_packages = [
        'flask', 'flask_cors', 'flask_sqlalchemy', 
        'flask_migrate', 'psycopg2', 'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n🚨 Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check environment configuration"""
    print("\n🔧 Checking Environment Configuration...")
    
    # Check for .env file
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"✅ Found {env_file}")
    else:
        print(f"⚠️  {env_file} not found - using defaults")
    
    # Check critical environment variables
    critical_vars = ['SECRET_KEY']
    optional_vars = ['DB_HOST', 'DB_PASSWORD', 'DATABASE_URL']
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)}")
        else:
            print(f"⚠️  {var}: Using default")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(10, len(value))}...")
        else:
            print(f"ℹ️  {var}: Not set")

def test_database_connection():
    """Test database connectivity"""
    print("\n🗄️  Testing Database Connection...")
    
    try:
        from app import create_app
        from models import db
        
        app = create_app(register_blueprints=False)
        
        with app.app_context():
            # Test database connection
            db.engine.execute('SELECT 1')
            print("✅ Database connection successful")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Check your database configuration in config.py")
        return False

def start_server():
    """Start the Flask server with enhanced error handling"""
    print("\n🚀 Starting Flask Server...")
    
    try:
        from app import create_app
        
        app = create_app()
        
        # Get port from environment or default to 5000
        port = int(os.environ.get("PORT", 5000))
        debug = os.environ.get("FLASK_ENV") != "production"
        
        print(f"🌐 Server starting on http://127.0.0.1:{port}")
        print(f"🔧 Debug mode: {debug}")
        print(f"⏰ Started at: {datetime.now()}")
        print("\n📋 Available endpoints:")
        print("  - GET  /              - Server info")
        print("  - GET  /health        - Health check")
        print("  - POST /api/auth/login - Login")
        print("  - GET  /api/superadmin/users - List users (auth required)")
        print("  - POST /api/superadmin/users - Create user (auth required)")
        print("\n🛑 Press Ctrl+C to stop the server")
        print("=" * 60)
        
        app.run(host="0.0.0.0", port=port, debug=debug)
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("\n💡 Troubleshooting steps:")
        print("1. Check if port 5000 is already in use")
        print("2. Verify database connection")
        print("3. Check for missing dependencies")
        sys.exit(1)

def main():
    """Main startup routine with comprehensive checks"""
    print("🚀 Employee Management Backend - Debug Startup")
    print("=" * 60)
    print(f"⏰ {datetime.now()}")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print("=" * 60)
    
    # Run all checks
    if not check_dependencies():
        print("\n❌ Dependency check failed!")
        sys.exit(1)
    
    check_environment()
    
    if not test_database_connection():
        print("\n⚠️  Database connection failed - server may still start but with limited functionality")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()