from app import create_app
from models.user import User

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        print("Testing User model directly...")
        
        # Get the admin user
        user = User.query.filter_by(email="admin@company.com").first()
        
        if user:
            print(f"✅ User found: {user.email}")
            print(f"User ID: {user.id}")
            print(f"User name: {user.name}")
            print(f"User role: {user.role}")
            
            # Test password check
            password_correct = user.check_password("admin123")
            print(f"Password check: {password_correct}")
            
            # Test to_dict method
            user_dict = user.to_dict()
            print(f"User dict keys: {list(user_dict.keys())}")
            print(f"Name in dict: {user_dict.get('name')}")
            
        else:
            print("❌ No user found with email admin@company.com")
            
        print("\nAll users:")
        for u in User.query.all():
            print(f"  - {u.email}: name='{u.name}', role='{u.role}'")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()