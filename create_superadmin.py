import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app
from models import db, User
import uuid

# Initialize app context
app = create_app()
app.app_context().push()

def create_superadmin(email, password):
    """Creates a superadmin user"""
    if User.query.filter_by(email=email).first():
        print(f"User with email {email} already exists.")
        return

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name="Super Admin",
        role="superadmin",
        created_by="system"
    )
    user.set_password(password)
    user.set_permissions(["all"])

    db.session.add(user)
    db.session.commit()
    print(f"Superadmin user {email} created successfully.")

if __name__ == "__main__":
    # You can change these credentials
    SUPERADMIN_EMAIL = "superadmin@company.com"
    SUPERADMIN_PASSWORD = "superadmin123"

    create_superadmin(SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD)