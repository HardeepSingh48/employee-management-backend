from app import create_app
from models import db
from models.user import User

app = create_app(register_blueprints=False)

with app.app_context():
    # Check what columns exist in users table
    inspector = db.inspect(db.engine)
    columns = inspector.get_columns('users')
    
    print("Existing columns in 'users' table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")
    
    # Check if any users exist
    users = User.query.all()
    print(f"\nNumber of users in database: {len(users)}")
    
    if users:
        user = users[0]
        print(f"First user attributes: {dir(user)}")