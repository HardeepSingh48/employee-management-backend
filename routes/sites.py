from flask import Blueprint, request, jsonify
from models import db
from models.site import Site
from routes.auth import token_required

sites_bp = Blueprint('sites', __name__)

@sites_bp.route('/', methods=['GET'])
@token_required
def get_sites(current_user):
    """Get all sites"""
    try:
        sites = Site.query.filter_by(is_active=True).all()
        return jsonify({
            "success": True,
            "data": [site.to_dict() for site in sites]
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@sites_bp.route('/', methods=['POST'])
@token_required
def create_site(current_user):
    """Create new site (admin only)"""
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        site = Site(
            site_id=data['site_id'],
            site_name=data['site_name'],
            location=data.get('location'),
            state=data.get('state'),
            created_by=current_user.email
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
        }), 400