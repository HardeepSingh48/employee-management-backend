from flask import Flask
from flask_cors import CORS
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
)
from models import db
from routes.employees import employees_bp
from routes.departments import departments_bp
from routes.salary_codes import salary_codes_bp
import os
from config import UPLOADS_DIR

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = SECRET_KEY

    # Enable CORS for all routes
    CORS(app, origins=["http://localhost:3000"])

    # Ensure uploads dir exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(salary_codes_bp, url_prefix="/api/salary-codes")

    # Add a simple root route for testing
    @app.route("/")
    def home():
        return {
            "message": "Employee Management System API",
            "version": "1.0",
            "endpoints": {
                "employees": "/api/employees",
                "departments": "/api/departments",
                "salary_codes": "/api/salary-codes"
            }
        }

    return app

app = create_app()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
