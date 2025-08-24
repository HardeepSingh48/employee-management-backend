from app import create_app
from models import db
from sqlalchemy import text

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text('''
                SELECT id, email, name, role, 
                       CASE WHEN name IS NULL THEN 'NULL' 
                            WHEN name = '' THEN 'EMPTY' 
                            ELSE 'HAS VALUE' 
                       END as name_status
                FROM users
            ''')).fetchall()
            
            print("Users in database:")
            for user in result:
                print(f"Email: {user.email}")
                print(f"Name: '{user.name}'")
                print(f"Name Status: {user.name_status}")
                print(f"Role: {user.role}")
                print("-" * 30)
                
    except Exception as e:
        print(f"Error: {e}")