import os
from werkzeug.utils import secure_filename
from config import UPLOADS_DIR, ALLOWED_EXTENSIONS

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file_storage, subfolder: str = "") -> str | None:
    if not file_storage or not allowed_file(file_storage.filename):
        return None
    fname = secure_filename(file_storage.filename)
    folder = os.path.join(UPLOADS_DIR, subfolder) if subfolder else UPLOADS_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, fname)
    file_storage.save(path)
    return path
