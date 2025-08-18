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
from routes.attendance import attendance_bp
from routes.salary import salary_bp
from routes.auth import auth_bp
from routes.employee_dashboard import employee_dashboard_bp
import os
from config import UPLOADS_DIR

def create_app():
    app = Flask(__name__)

    # Disable strict slashes to avoid redirect issues with CORS
    app.url_map.strict_slashes = False

    # Enable CORS for all routes with specific configuration
    # Allow your frontend domain in production
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ]

    # Add your production frontend URL here when you deploy it
    # allowed_origins.append("https://your-frontend-domain.com")

    CORS(app,
         origins=allowed_origins,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization"])

    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = SECRET_KEY

    # Ensure uploads dir exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    db.init_app(app)

    # Register all blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(employee_dashboard_bp, url_prefix="/api/employee")
    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(salary_codes_bp, url_prefix="/api/salary-codes")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
    app.register_blueprint(salary_bp, url_prefix="/api/salary")

    # Add a simple root route for testing
    @app.route("/")
    def home():
        return {
            "message": "Employee Management System API",
            "version": "2.0",
            "endpoints": {
                "auth": "/api/auth",
                "employee_dashboard": "/api/employee",
                "employees": "/api/employees",
                "departments": "/api/departments",
                "salary_codes": "/api/salary-codes",
                "attendance": "/api/attendance",
                "salary": "/api/salary"
            }
        }

    return app

app = create_app()

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
