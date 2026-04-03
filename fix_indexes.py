from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        print("Applying unique partial indexes to database...")
        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_adhar
            ON employees(adhar_number)
            WHERE is_deleted = FALSE
            AND adhar_number IS NOT NULL
            AND adhar_number != ''
            AND adhar_number != '000000000000'
        """))
        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_phone
            ON employees(phone_number)
            WHERE is_deleted = FALSE
            AND phone_number IS NOT NULL
            AND phone_number != ''
            AND phone_number != '9999999999'
        """))
        db.session.commit()
        print("SUCCESS! Indexes applied.")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: {e}")
