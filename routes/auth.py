from flask import Blueprint, request, jsonify, current_app
from models import db
from models.user import User
from models.employee import Employee
from datetime import datetime, timedelta
import jwt
from functools import wraps

auth_bp = Blueprint("auth", __name__)

def generate_token(user):
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'employee_id': user.employee_id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user or not current_user.is_active:
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

@auth_bp.route("/login", methods=["POST"])
def login():
    """Employee/Admin login endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return jsonify({
                "success": False,
                "message": "Account is temporarily locked. Please try again later."
            }), 401
        
        # Check password
        if not user.check_password(password):
            # Increment login attempts
            user.login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            db.session.commit()
            
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                "success": False,
                "message": "Account is deactivated"
            }), 401
        
        # Successful login - reset attempts and update last login
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate token
        token = generate_token(user)
        
        # Get employee details if available
        employee_data = None
        if user.employee_id and user.employee:
            employee_data = {
                'employee_id': user.employee.employee_id,
                'first_name': user.employee.first_name,
                'last_name': user.employee.last_name,
                'department_id': user.employee.department_id,
                'designation': user.employee.designation,
                'salary_code': user.employee.salary_code
            }
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "data": {
                "user": user.to_dict(),
                "employee": employee_data,
                "token": token
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Login error: {str(e)}"
        }), 500

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register new user (admin only for now)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role', 'employee')
        employee_id = data.get('employee_id')
        
        if not email or not password or not name:
            return jsonify({
                "success": False,
                "message": "Email, password, and name are required"
            }), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                "success": False,
                "message": "User with this email already exists"
            }), 400
        
        # Validate employee_id if provided
        employee = None
        if employee_id:
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            if not employee:
                return jsonify({
                    "success": False,
                    "message": "Employee not found"
                }), 400
        
        # Create new user
        user = User(
            email=email,
            name=name,
            role=role,
            employee_id=employee_id,
            department=data.get('department'),
            created_by=data.get('created_by', 'system')
        )
        user.set_password(password)
        
        # Set default permissions based on role
        if role == 'admin':
            user.set_permissions(['all'])
        elif role == 'employee':
            user.set_permissions(['view_profile', 'mark_attendance', 'view_attendance'])
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = generate_token(user)
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "data": {
                "user": user.to_dict(),
                "token": token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Registration error: {str(e)}"
        }), 500

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user(current_user):
    """Get current user information"""
    try:
        employee_data = None
        if current_user.employee_id and current_user.employee:
            employee_data = {
                'employee_id': current_user.employee.employee_id,
                'first_name': current_user.employee.first_name,
                'last_name': current_user.employee.last_name,
                'department_id': current_user.employee.department_id,
                'designation': current_user.employee.designation,
                'salary_code': current_user.employee.salary_code,
                'phone_number': current_user.employee.phone_number,
                'email': current_user.employee.email
            }
        
        return jsonify({
            "success": True,
            "data": {
                "user": current_user.to_dict(),
                "employee": employee_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting user info: {str(e)}"
        }), 500

@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout(current_user):
    """Logout user (token will be invalidated on client side)"""
    return jsonify({
        "success": True,
        "message": "Logged out successfully"
    }), 200

# --- Added endpoints to match frontend expectations ---

@auth_bp.route("/refresh", methods=["POST"])
@token_required
def refresh_token(current_user):
    """Issue a new JWT for the current user"""
    try:
        token = generate_token(current_user)
        return jsonify({
            "success": True,
            "message": "Token refreshed",
            "data": {"token": token}
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Token refresh error: {str(e)}"
        }), 500


@auth_bp.route("/profile", methods=["PUT"])
@token_required
def update_profile(current_user):
    """Update current user's profile"""
    try:
        data = request.get_json() or {}

        # Allow limited fields to be updated
        allowed_fields = ["name", "department", "profile_image"]
        for field in allowed_fields:
            if field in data:
                setattr(current_user, field, data[field])

        current_user.updated_by = data.get("updated_by", current_user.email)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Profile updated successfully",
            "data": current_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Profile update error: {str(e)}"
        }), 500


@auth_bp.route("/change-password", methods=["PUT"])
@token_required
def change_password(current_user):
    """Change current user's password"""
    try:
        data = request.get_json() or {}
        current_password = data.get("currentPassword")
        new_password = data.get("newPassword")

        if not current_password or not new_password:
            return jsonify({
                "success": False,
                "message": "Current password and new password are required"
            }), 400

        if not current_user.check_password(current_password):
            return jsonify({
                "success": False,
                "message": "Current password is incorrect"
            }), 400

        current_user.set_password(new_password)
        current_user.updated_by = current_user.email
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Password changed successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Password change error: {str(e)}"
        }), 500
