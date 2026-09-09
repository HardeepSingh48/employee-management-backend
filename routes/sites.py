from flask import Blueprint, request, jsonify
from models import db
from models.site import Site
from routes.auth import token_required
import pandas as pd
import io
import uuid
from datetime import datetime

sites_bp = Blueprint('sites', __name__)

def generate_site_id():
    """Generate a unique site ID in the format SITE-XXXXXXXX"""
    return f"SITE-{uuid.uuid4().hex[:8].upper()}"

@sites_bp.route('/', methods=['GET'])
@token_required
def get_sites(current_user):
    """Get all sites with pagination and search"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '', type=str)
        
        # Base query
        query = Site.query
        
        # Apply search filter if provided
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Site.site_id.ilike(search_filter),
                    Site.site_name.ilike(search_filter),
                    Site.state.ilike(search_filter)
                )
            )
        
        # Paginate results
        sites = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            "success": True,
            "data": [site.to_dict() for site in sites.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": sites.total,
                "pages": sites.pages
            }
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@sites_bp.route('/', methods=['POST'])
@token_required
def create_site(current_user):
    """Create new site (admin and superadmin only)"""
    if current_user.role not in ['admin', 'admin1', 'admin2', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json(silent=True) or {}

        site_name = Site.normalize_name(data.get('site_name'))
        state = str(data.get('state') or '').strip()
        
        # Validate required fields
        if not site_name or not state:
            return jsonify({
                "success": False,
                "message": "site_name and state are required"
            }), 400

        existing_site = Site.find_by_name(site_name)
        if existing_site:
            return jsonify({
                "success": False,
                "message": f"A site with the name '{existing_site.site_name}' already exists.",
                "existing_site": existing_site.to_dict(),
            }), 409
        
        # Generate site_id
        site_id = generate_site_id()
        
        # Create site
        site = Site(
            site_id=site_id,
            site_name=site_name,
            location=data.get('location'),
            state=state,
            created_by=current_user.email,  # Set created_by to current user
            is_active=True
        )
        db.session.add(site)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Site created successfully",
            "data": site.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@sites_bp.route('/bulk', methods=['POST'])
@token_required
def bulk_import_sites(current_user):
    """Bulk import sites from Excel/CSV file (admin and superadmin only)"""
    if current_user.role not in ['admin', 'admin1', 'admin2', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No file provided"
            }), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({
                "success": False,
                "message": "No file selected"
            }), 400
        
        # Read file based on extension
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({
                "success": False,
                "message": "Unsupported file format. Please upload CSV or Excel file."
            }), 400
        
        # Validate required columns
        required_columns = ['site_name', 'state']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({
                    "success": False,
                    "message": f"Missing required column: {col}"
                }), 400
        
        # Process each row
        created_count = 0
        errors = []
        seen_names = set()
        
        for index, row in df.iterrows():
            try:
                site_name = Site.normalize_name(row.get('site_name'))
                state = str(row.get('state') or '').strip()
                site_key = site_name.casefold()
                if not site_name or not state:
                    errors.append(f"Row {index + 1}: site_name and state are required")
                    continue
                if site_key in seen_names:
                    errors.append(f"Row {index + 1}: Duplicate site name '{site_name}' in the upload")
                    continue
                seen_names.add(site_key)

                # Check if site already exists (by site_name and state)
                existing_site = Site.find_by_name(site_name)
                
                if existing_site:
                    if existing_site.state.strip().casefold() != state.casefold():
                        errors.append(
                            f"Row {index + 1}: Site name '{site_name}' already exists with state '{existing_site.state}'"
                        )
                        continue
                    # Update existing site
                    existing_site.location = row.get('location', existing_site.location)
                    existing_site.updated_date = datetime.utcnow().date()
                    existing_site.updated_by = current_user.email
                else:
                    # Create new site
                    site = Site(
                        site_id=generate_site_id(),
                        site_name=site_name,
                        location=row.get('location'),
                        state=state,
                        created_by=current_user.email,
                        is_active=True
                    )
                    db.session.add(site)
                created_count += 1
                    
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Bulk import completed. Created: {created_count}",
            "created": created_count,
            "errors": errors
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@sites_bp.route('/<site_id>', methods=['PUT'])
@token_required
def update_site(current_user, site_id):
    """Update site details (admin and superadmin only)"""
    if current_user.role not in ['admin', 'admin1', 'admin2', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        site = Site.query.get(site_id)
        if not site:
            return jsonify({
                "success": False,
                "message": "Site not found"
            }), 404
        
        data = request.get_json(silent=True) or {}
        
        # Update fields if provided
        if 'site_name' in data:
            site_name = Site.normalize_name(data.get('site_name'))
            if not site_name:
                return jsonify({
                    "success": False,
                    "message": "site_name cannot be empty"
                }), 400

            duplicate_site = Site.find_by_name(site_name, exclude_site_id=site.site_id)
            if duplicate_site:
                return jsonify({
                    "success": False,
                    "message": f"A site with the name '{duplicate_site.site_name}' already exists.",
                    "existing_site": duplicate_site.to_dict(),
                }), 409
            site.site_name = site_name
        if 'location' in data:
            site.location = data['location']
        if 'state' in data:
            state = str(data.get('state') or '').strip()
            if not state:
                return jsonify({
                    "success": False,
                    "message": "state cannot be empty"
                }), 400
            site.state = state
        if 'is_active' in data:
            site.is_active = data['is_active']
            
        # Update updated_date and updated_by
        site.updated_date = datetime.utcnow().date()
        site.updated_by = current_user.email
            
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Site updated successfully",
            "data": site.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@sites_bp.route('/<site_id>', methods=['DELETE'])
@token_required
def delete_site(current_user, site_id):
    """Delete site (admin and superadmin only)"""
    if current_user.role not in ['admin', 'admin1', 'admin2', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        site = Site.query.get(site_id)
        if not site:
            return jsonify({
                "success": False,
                "message": "Site not found"
            }), 404
        
        db.session.delete(site)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Site deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
