# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration - prioritize Supabase setup
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Build the database URI
if DB_HOST and DB_PASSWORD:
    # Use Supabase or custom database configuration
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # Fallback to DATABASE_URL if provided (for deployment platforms)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("Database configuration missing! Please set DB_HOST, DB_PASSWORD, etc. in your .env file")

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Application configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads/employees")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "pdf", "doc", "docx", "xlsx", "xls"}