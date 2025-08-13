# config.py
import os

DB_USER = os.getenv("DB_USER", "sspl_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "sspl_db")

SQLALCHEMY_DATABASE_URI = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# uploads
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads/employees")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "pdf", "doc", "docx", "xlsx", "xls"}
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
