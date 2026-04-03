from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Check columns of employees table
        result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'employees'")).fetchall()
        columns = [row[0] for row in result]
        if 'is_deleted' in columns:
            print("SUCCESS: 'is_deleted' column EXISTS in employees table.")
        else:
            print("ERROR: 'is_deleted' column does NOT exist in employees table.")
    except Exception as e:
        print(f"ERROR: {e}")
