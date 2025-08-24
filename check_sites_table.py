from app import create_app
from models import db

app = create_app(register_blueprints=False)

with app.app_context():
    try:
        # Check if sites table exists
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print("Existing tables:", tables)
        
        if 'sites' in tables:
            print("Sites table exists")
            # Check columns
            columns = inspector.get_columns('sites')
            print("Sites table columns:")
            for column in columns:
                print(f"  - {column['name']} ({column['type']})")
        else:
            print("Sites table does not exist")
    except Exception as e:
        print(f"Error: {e}")