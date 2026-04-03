from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        print("Applying soft delete columns directly to database...")
        db.session.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false"))
        db.session.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE"))
        db.session.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS left_on DATE"))
        db.session.commit()
        print("SUCCESS! Columns added to 'employees' table.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {e}")
