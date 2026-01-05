from flask import Blueprint, request, jsonify
from models import db, User
import uuid
from functools import wraps
from routes.auth import token_required

superadmin_bp = Blueprint('superadmin_bp', __name__)

# Custom decorator to check for superadmin role
def superadmin_required(fn):
    @wraps(fn)
    def wrapper(current_user, *args, **kwargs):
        if not current_user or current_user.role != 'superadmin':
            return jsonify({"success": False, "message": "Superadmin access required"}), 403
        return fn(current_user, *args, **kwargs)
    return wrapper

# Route to create a new admin or supervisor
@superadmin_bp.route('/superadmin/users', methods=['POST'])
@token_required
@superadmin_required
def create_user(current_user):
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role')
    site_id = data.get('site_id')

    if not all([password, name, role]):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    # Convert empty strings to None
    email = email if email and email.strip() else None
    username = username if username and username.strip() else None

    if not email and not username:
        return jsonify({"success": False, "message": "Either email or username is required"}), 400

    if role not in ['admin', 'admin1', 'admin2', 'supervisor']:
        return jsonify({"success": False, "message": "Invalid role"}), 400

    # Validate site_id for supervisor role
    if role == 'supervisor' and not site_id:
        return jsonify({"success": False, "message": "Site ID is required for supervisor role"}), 400

    # Check for existing email if provided
    if email is not None and User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "User with this email already exists"}), 409

    # Check for existing username if provided
    if username is not None and User.query.filter_by(username=username).first():
        return jsonify({"success": False, "message": "User with this username already exists"}), 409

    # Validate site exists if site_id is provided
    if site_id:
        from models.site import Site
        site = Site.query.filter_by(site_id=site_id).first()
        if not site:
            return jsonify({"success": False, "message": "Invalid site ID"}), 400

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        name=name,
        role=role,
        site_id=site_id if role == 'supervisor' else None,
        created_by=current_user.email
    )
    user.set_password(password)
    
    # Set permissions based on role
    if role in ['admin', 'admin1', 'admin2']:
        user.set_permissions(['all'])
    elif role == 'supervisor':
        user.set_permissions(['view_employees', 'mark_attendance', 'view_reports'])
    
    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True, "message": f"{role.capitalize()} created successfully"}), 201

# Route to get all admins and supervisors
@superadmin_bp.route('/superadmin/users', methods=['GET'])
@token_required
@superadmin_required
def get_users(current_user):
    users = User.query.filter(User.role.in_(['admin', 'admin1', 'admin2', 'supervisor'])).all()
    
    users_data = []
    for user in users:
        user_dict = {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'username': user.username,
            'role': user.role,
            'site_id': user.site_id
        }
        
        # Add site information for supervisors
        if user.role == 'supervisor' and user.site_id:
            try:
                from models.site import Site
                site = Site.query.filter_by(site_id=user.site_id).first()
                if site:
                    user_dict['site'] = {
                        'site_name': site.site_name,
                        'state': site.state
                    }
            except Exception as e:
                print(f"Error fetching site for user {user.id}: {e}")
        
        users_data.append(user_dict)
    
    return jsonify({
        "success": True,
        "data": users_data
    }), 200

# Route to update a user
@superadmin_bp.route('/superadmin/users/<user_id>', methods=['PUT'])
@token_required
@superadmin_required
def update_user(current_user, user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Prevent editing superadmin users
        if user.role == 'superadmin':
            return jsonify({"success": False, "message": "Cannot edit superadmin users"}), 403
        
        data = request.get_json()

        # Convert empty strings to None
        email_data = data.get('email')
        username_data = data.get('username')
        email_data = email_data if email_data and email_data.strip() else None
        username_data = username_data if username_data and username_data.strip() else None

        # Validate that either username or email is provided
        if email_data is None and username_data is None:
            return jsonify({"success": False, "message": "Either username or email is required"}), 400

        # Update fields if provided
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            # Check if email is already taken by another user
            if email_data is not None:
                existing_user = User.query.filter(User.email == email_data, User.id != user_id).first()
                if existing_user:
                    return jsonify({"success": False, "message": "Email already exists"}), 400
            user.email = email_data
        if 'username' in data:
            # Check if username is already taken by another user
            if username_data is not None:
                existing_user = User.query.filter(User.username == username_data, User.id != user_id).first()
                if existing_user:
                    return jsonify({"success": False, "message": "Username already exists"}), 400
            user.username = username_data
        if 'role' in data:
            if data['role'] not in ['admin', 'admin1', 'admin2', 'supervisor']:
                return jsonify({"success": False, "message": "Invalid role"}), 400
            user.role = data['role']
        if 'site_id' in data:
            if user.role == 'supervisor' and data['site_id']:
                # Validate site exists
                from models.site import Site
                site = Site.query.filter_by(site_id=data['site_id']).first()
                if not site:
                    return jsonify({"success": False, "message": "Invalid site ID"}), 400
                user.site_id = data['site_id']
            elif user.role in ['admin', 'admin1', 'admin2']:
                user.site_id = None  # Admins don't need site assignment
        
        # Update password if provided
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        user.updated_by = current_user.email
        db.session.commit()
        
        return jsonify({"success": True, "message": "User updated successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Route to delete a user
@superadmin_bp.route('/superadmin/users/<user_id>', methods=['DELETE'])
@token_required
@superadmin_required
def delete_user(current_user, user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Prevent deleting superadmin users
        if user.role == 'superadmin':
            return jsonify({"success": False, "message": "Cannot delete superadmin users"}), 403
        
        # Prevent self-deletion
        if user.id == current_user.id:
            return jsonify({"success": False, "message": "Cannot delete your own account"}), 403
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"success": True, "message": "User deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500