from flask import Flask, request, make_response
from flask_cors import CORS
from datetime import datetime
from config import (
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
    CORS_ORIGINS,
    ADDITIONAL_CORS_ORIGINS,
    COOLIFY_FQDN,  # IMPORT THIS!
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

    # Build allowed origins list
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://employee-management-frontend-kohl-eight.vercel.app",
        "https://ssplsecurity.in",
        "https://api.ssplsecurity.in",  # Add your API domain explicitly
    ]

    # Add production origins from config
    if CORS_ORIGINS:
        allowed_origins.extend([origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()])

    # Add additional origins from environment variable if set
    if ADDITIONAL_CORS_ORIGINS:
        allowed_origins.extend([origin.strip() for origin in ADDITIONAL_CORS_ORIGINS.split(",") if origin.strip()])
    
    # Add Coolify FQDN if present
    if COOLIFY_FQDN:
        allowed_origins.append(COOLIFY_FQDN)

    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys(allowed_origins))

    print(f"CORS allowed origins: {allowed_origins}")

    # Configure CORS with enhanced settings
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
         ],
         supports_credentials=True,
         expose_headers=["Content-Type", "Authorization", "X-Total-Count"],
         send_wildcard=False,
         automatic_options=True,
         max_age=86400)

    # Simplified CORS headers handler
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get('Origin')
        
        # If origin is in allowed list, set it
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        # Fallback for production
        elif not origin:
            response.headers['Access-Control-Allow-Origin'] = 'https://ssplsecurity.in'
        
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin, X-CSRF-Token'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '86400'

        # Debug logging
        if os.getenv("FLASK_ENV") == "production" or os.getenv("DEBUG_CORS") == "true":
            print(f"CORS Debug - Origin: {origin}, Allowed: {response.headers.get('Access-Control-Allow-Origin')}")

        return response
    
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = SECRET_KEY

    # SQLAlchemy Connection Pooling Configuration
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 30,
        'max_overflow': 50,
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_timeout': 60,
        'echo': False
    }

    # Ensure uploads dir exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    db.init_app(app)
    migrate = Migrate(app, db)

    # Demo users seeding
    if os.getenv("SEED_DEMO_USERS", "").lower() == "true":
        with app.app_context():
            try:
                admin = User.query.filter_by(email="admin@company.com").first()
                if not admin:
                    admin = User(
                        email="admin@company.com",
                        name="Admin User",
                        role="admin",
                        created_by="system"
                    )
                    admin.set_password("admin123")
                    admin.set_permissions(["all"])
                    db.session.add(admin)

                employee_user = User.query.filter_by(email="employee@company.com").first()
                if not employee_user:
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
                try:
                    db.session.rollback()
                except Exception:
                    pass
                print(f"[WARN] Demo user seeding failed: {seed_err}")

    # Register blueprints
    if register_blueprints:
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
        from routes.id_cards import id_cards_bp

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
        app.register_blueprint(id_cards_bp, url_prefix="/api/id-cards")
        app.register_blueprint(superadmin_bp, url_prefix="/api")

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

    @app.route("/health")
    def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    return app

if os.getenv("CREATE_APP_ON_IMPORT", "1") not in ("0", "false", "False"):
    app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"

    try:
        app
    except NameError:
        app = create_app()

    app.run(host="0.0.0.0", port=port, debug=debug)