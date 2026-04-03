from app import create_app
from models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        print("alembic_version:")
        for row in result:
            print(f"- {row[0]}")
    except Exception as e:
        print(f"ERROR: {e}")
