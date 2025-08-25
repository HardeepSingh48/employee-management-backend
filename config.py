# config.py
import os

DATABASE_URL = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER", "sspl_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sspl_db")

# Prefer full DATABASE_URL if provided (Render provides this). Fallback to discrete vars.
SQLALCHEMY_DATABASE_URI = (
    DATABASE_URL
    or f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    or "postgresql://employee_management_db_zwaz_user:iJCGc6DAulfzuW758GB3L2yMJOYUPtWY@dpg-d2hl5j24d50c739hsm30-a.singapore-postgres.render.com/employee_management_db_zwaz"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# uploads
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads/employees")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "pdf", "doc", "docx", "xlsx", "xls"}
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
