from flask import Flask, request, make_response
from flask_cors import CORS
from datetime import datetime
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
)
from models import db
import os
from config import UPLOADS_DIR
from models.user import User
from models.employee import Employee
from flask_migrate import Migrate
from models.site import Site
from routes.superadmin import superadmin_bp

def create_app(register_blueprints: bool = True):
    app = Flask(__name__)

    # Disable strict slashes to avoid redirect issues with CORS
    app.url_map.strict_slashes = False

    # Enable CORS for all routes with specific configuration
    # Allow your frontend domain in production and development
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://employee-management-frontend-kohl-eight.vercel.app"
    ]

    # Add additional origins from environment variable if set
    additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "")
    if additional_origins:
        allowed_origins.extend([origin.strip() for origin in additional_origins.split(",") if origin.strip()])

    print(f"CORS allowed origins: {allowed_origins}")

    # Configure CORS with enhanced settings for development/testing
    CORS(app,
         origins=allowed_origins,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
         allow_headers=[
             "Content-Type",
             "Authorization",
             "X-Requested-With",
             "Accept",
             "Origin",
             "Access-Control-Allow-Origin",
             "X-CSRF-Token",
             "X-Requested-With"
         ],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization", "X-Total-Count"],
         send_wildcard=False,
         automatic_options=True,
         max_age=86400)  # Cache preflight for 24 hours
    
    # Add explicit OPTIONS handler for debugging
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin', '*')
            # Check if origin is in allowed origins
            if origin in allowed_origins or origin == '*':
                response = make_response()
                response.headers.add("Access-Control-Allow-Origin", origin)
                response.headers.add('Access-Control-Allow-Headers', "Content-Type, Authorization, X-Requested-With, Accept, Origin, Access-Control-Allow-Origin, X-CSRF-Token, X-Requested-With")
                response.headers.add('Access-Control-Allow-Methods', "GET, POST, PUT, DELETE, OPTIONS, PATCH")
                response.headers.add('Access-Control-Allow-Credentials', "true")
                response.headers.add('Access-Control-Max-Age', "86400")
                return response

    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = SECRET_KEY

    # Ensure uploads dir exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    db.init_app(app)

    migrate = Migrate(app, db)

    # Optionally seed demo users in production by setting SEED_DEMO_USERS=true
    if os.getenv("SEED_DEMO_USERS", "").lower() == "true":
        with app.app_context():
            try:
                # Admin user
                admin = User.query.filter_by(email="admin@company.com").first()
                if not admin:
                    admin = User(
                        email="admin@company.com",
                        name="Admin User",
                        role="admin",
                        created_by="system"
                    )
                    admin.set_password("admin123")
                    admin.set_permissions(["all"])  # full access
                    db.session.add(admin)

                # Employee user and minimal employee profile
                employee_user = User.query.filter_by(email="employee@company.com").first()
                if not employee_user:
                    # Ensure an employee record exists
                    demo_employee_id = "EMPDEMO001"
                    employee = Employee.query.filter_by(employee_id=demo_employee_id).first()
                    if not employee:
                        employee = Employee(
                            employee_id=demo_employee_id,
                            first_name="Demo",
                            last_name="Employee",
                            email="employee@company.com",
                            designation="Associate",
                            employment_status="Active",
                            created_by="system"
                        )
                        db.session.add(employee)

                    employee_user = User(
                        email="employee@company.com",
                        name="Demo Employee",
                        role="employee",
                        employee_id=demo_employee_id,
                        created_by="system"
                    )
                    employee_user.set_password("emp123")
                    employee_user.set_permissions(["view_profile", "mark_attendance", "view_attendance"])
                    db.session.add(employee_user)

                db.session.commit()
            except Exception as seed_err:
                # Do not crash app on seed errors; log and continue
                try:
                    db.session.rollback()
                except Exception:
                    pass
                print(f"[WARN] Demo user seeding failed: {seed_err}")

    # Register all blueprints (optional for scripts)
    if register_blueprints:
        # Import lazily to avoid importing heavy dependencies when not needed
        from routes.auth import auth_bp
        from routes.employee_dashboard import employee_dashboard_bp
        from routes.employees import employees_bp
        from routes.departments import departments_bp
        from routes.salary_codes import salary_codes_bp
        from routes.attendance import attendance_bp
        from routes.salary import salary_bp
        from routes.forms import forms_bp
        from routes.sites import sites_bp
        from routes.deductions import deductions_bp
        from routes.payroll import payroll_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(employee_dashboard_bp, url_prefix="/api/employee")
        app.register_blueprint(employees_bp, url_prefix="/api/employees")
        app.register_blueprint(departments_bp, url_prefix="/api/departments")
        app.register_blueprint(salary_codes_bp, url_prefix="/api/salary-codes")
        app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
        app.register_blueprint(salary_bp, url_prefix="/api/salary")
        app.register_blueprint(forms_bp, url_prefix="/api/forms")
        app.register_blueprint(sites_bp, url_prefix="/api/sites")
        app.register_blueprint(deductions_bp, url_prefix="/api/deductions")
        app.register_blueprint(payroll_bp, url_prefix="/api/payroll")
        app.register_blueprint(superadmin_bp, url_prefix="/api")

    # Add a simple root route for testing
    @app.route("/")
    def home():
        return {
            "message": "Employee Management System API",
            "version": "2.0",
            "status": "running",
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

    # Add health check route
    @app.route("/health")
    def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    # Rely on Flask-CORS for preflight handling to avoid conflicts with credentials

    return app

# Create the WSGI app when importing this module (needed for gunicorn),
# but allow scripts to disable this by setting CREATE_APP_ON_IMPORT=0
if os.getenv("CREATE_APP_ON_IMPORT", "1") not in ("0", "false", "False"):
    app = create_app()

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"

    # Ensure app exists even if CREATE_APP_ON_IMPORT disabled
    try:
        app
    except NameError:
        app = create_app()

    app.run(host="0.0.0.0", port=port, debug=debug)
