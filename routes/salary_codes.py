from flask import Blueprint, request, jsonify
from models import db
from models.wage_master import WageMaster
from utils.validators import validate_wage_master_data
import re

salary_codes_bp = Blueprint("salary_codes_api", __name__)

@salary_codes_bp.route("/test", methods=["GET", "POST", "OPTIONS"])
def test_cors():
    """Test endpoint to verify CORS is working"""
    return jsonify({
        "success": True,
        "message": "CORS test successful",
        "method": request.method
    })

@salary_codes_bp.route("/create", methods=["POST", "OPTIONS"])
def create_salary_code_alt():
    """Alternative endpoint for creating salary codes (without trailing slash issues)"""
    # print(f"🔍 Alternative endpoint - Received {request.method} request to {request.url}")

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        # print("✅ Alternative endpoint - Handling OPTIONS preflight request")
        return '', 200

    # Delegate to the main create function logic
    return create_salary_code()

@salary_codes_bp.route("/", methods=["GET"])
def list_salary_codes():
    """List all active salary codes"""
    try:
        wage_masters = WageMaster.query.filter_by(is_active=True).all()
        
        salary_codes = []
        for wage in wage_masters:
            salary_codes.append({
                "id": wage.id,
                "salary_code": wage.salary_code,
                "site_name": wage.site_name,
                "rank": wage.rank,
                "state": wage.state,
                "base_wage": wage.base_wage,
                "skill_level": wage.skill_level,
                "is_active": wage.is_active,
                "created_at": wage.created_at.isoformat() if wage.created_at else None,
                "display_name": f"{wage.salary_code} - {wage.site_name} | {wage.rank} | {wage.state} (₹{wage.base_wage})"
            })
        
        return jsonify({
            "success": True,
            "data": salary_codes,
            "count": len(salary_codes),
            "message": f"Found {len(salary_codes)} salary codes"
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@salary_codes_bp.route("/", methods=["POST", "OPTIONS"])
def create_salary_code():
    """Create a new salary code"""
    # print(f"🔍 Received {request.method} request to {request.url}")
    # print(f"🔍 Request headers: {dict(request.headers)}")
    # print(f"🔍 Request origin: {request.headers.get('Origin', 'No origin')}")

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        # print("✅ Handling OPTIONS preflight request")
        return '', 200

    try:
        if request.is_json:
            payload = request.get_json()
            # print(f"📦 JSON payload: {payload}")
        else:
            payload = request.form.to_dict()
            # print(f"📦 Form payload: {payload}")

        # Validate required fields
        required_fields = ['site_name', 'rank', 'state', 'base_wage']
        missing_fields = [field for field in required_fields if not payload.get(field)]
        if missing_fields:
            return jsonify({
                "success": False, 
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Validate the data (skip skill_level validation for salary code creation)
        errors = validate_wage_master_data(payload, validate_skill_level=False)
        if errors:
            return jsonify({"success": False, "message": "Validation errors", "errors": errors}), 400

        # Check if combination already exists
        existing_wage = WageMaster.query.filter_by(
            site_name=payload["site_name"],
            rank=payload["rank"],
            state=payload["state"],
            is_active=True
        ).first()
        
        if existing_wage:
            return jsonify({
                "success": False, 
                "message": f"Salary code already exists for this combination: {existing_wage.salary_code}",
                "existing_data": {
                    "salary_code": existing_wage.salary_code,
                    "base_wage": existing_wage.base_wage
                }
            }), 400

        # Generate salary code
        salary_code = _generate_salary_code(
            payload["site_name"], 
            payload["rank"], 
            payload["state"]
        )

        # Set default skill level - will be updated during employee registration
        skill_level = "Not Specified"  # Default value, will be set when employee is registered

        wage_master = WageMaster(
            salary_code=salary_code,
            site_name=payload["site_name"],
            rank=payload["rank"],
            state=payload["state"],
            base_wage=float(payload["base_wage"]),
            skill_level=skill_level,
            created_by=payload.get("created_by", "admin")
        )
        
        db.session.add(wage_master)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Salary code created successfully",
            "data": {
                "id": wage_master.id,
                "salary_code": wage_master.salary_code,
                "site_name": wage_master.site_name,
                "rank": wage_master.rank,
                "state": wage_master.state,
                "base_wage": wage_master.base_wage,
                "skill_level": wage_master.skill_level,
                "display_name": f"{wage_master.salary_code} - {wage_master.site_name} | {wage_master.rank} | {wage_master.state} (₹{wage_master.base_wage})"
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


@salary_codes_bp.route("/bulk", methods=["POST"])
def bulk_create_salary_codes():
    """Bulk create salary codes from array of data"""
    try:
        if request.is_json:
            payload = request.get_json()
        else:
            return jsonify({"success": False, "message": "JSON data required for bulk creation"}), 400

        salary_codes_data = payload.get("salary_codes", [])
        if not salary_codes_data:
            return jsonify({"success": False, "message": "salary_codes array is required"}), 400

        created_codes = []
        errors = []

        for idx, code_data in enumerate(salary_codes_data):
            try:
                # Validate required fields
                required_fields = ['site_name', 'rank', 'state', 'base_wage']
                missing_fields = [field for field in required_fields if not code_data.get(field)]
                if missing_fields:
                    errors.append(f"Row {idx + 1}: Missing fields: {', '.join(missing_fields)}")
                    continue

                # Check if combination already exists
                existing_wage = WageMaster.query.filter_by(
                    site_name=code_data["site_name"],
                    rank=code_data["rank"],
                    state=code_data["state"],
                    is_active=True
                ).first()
                
                if existing_wage:
                    errors.append(f"Row {idx + 1}: Combination already exists with code: {existing_wage.salary_code}")
                    continue

                # Generate salary code
                salary_code = _generate_salary_code(
                    code_data["site_name"], 
                    code_data["rank"], 
                    code_data["state"]
                )

                wage_master = WageMaster(
                    salary_code=salary_code,
                    site_name=code_data["site_name"],
                    rank=code_data["rank"],
                    state=code_data["state"],
                    base_wage=float(code_data["base_wage"]),
                    skill_level="Not Specified",  # Default value, will be set during employee registration
                    created_by=code_data.get("created_by", "admin")
                )
                
                db.session.add(wage_master)
                created_codes.append({
                    "salary_code": salary_code,
                    "site_name": code_data["site_name"],
                    "rank": code_data["rank"],
                    "state": code_data["state"],
                    "base_wage": float(code_data["base_wage"])
                })

            except Exception as e:
                errors.append(f"Row {idx + 1}: {str(e)}")

        if created_codes:
            db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Bulk creation completed. Created: {len(created_codes)}, Errors: {len(errors)}",
            "data": {
                "created_count": len(created_codes),
                "created_codes": created_codes,
                "error_count": len(errors),
                "errors": errors
            }
        }), 201 if created_codes else 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


def _generate_salary_code(site_name: str, rank: str, state: str) -> str:
    """Generate salary code from site name, rank, and state"""
    # Clean and format inputs
    site_clean = re.sub(r'[^a-zA-Z]', '', site_name.upper())
    rank_clean = re.sub(r'[^a-zA-Z]', '', rank.upper())
    state_clean = re.sub(r'[^a-zA-Z]', '', state.upper())

    # Extract site prefix (first 3 characters)
    site_prefix = site_clean[:3] if len(site_clean) >= 3 else site_clean

    # Basic code format: SITE + RANK + STATE
    base_code = f"{site_prefix}{rank_clean}{state_clean}"

    # Check if code already exists
    existing_code = WageMaster.query.filter(WageMaster.salary_code == base_code).first()

    if not existing_code:
        return base_code

    # If exists, add a numeric suffix
    counter = 1
    while True:
        new_code = f"{base_code}{counter:02d}"
        existing = WageMaster.query.filter(WageMaster.salary_code == new_code).first()
        if not existing:
            return new_code
        counter += 1


@salary_codes_bp.route("/<salary_code>", methods=["GET"])
def get_salary_code(salary_code):
    """Get salary code details"""
    try:
        wage = WageMaster.query.filter_by(salary_code=salary_code, is_active=True).first()
        if not wage:
            return jsonify({"success": False, "message": "Salary code not found"}), 404
        
        return jsonify({
            "success": True,
            "data": {
                "id": wage.id,
                "salary_code": wage.salary_code,
                "site_name": wage.site_name,
                "rank": wage.rank,
                "state": wage.state,
                "base_wage": wage.base_wage,
                "skill_level": wage.skill_level,
                "is_active": wage.is_active,
                "created_at": wage.created_at.isoformat() if wage.created_at else None,
                "display_name": f"{wage.salary_code} - {wage.site_name} | {wage.rank} | {wage.state} (₹{wage.base_wage})"
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@salary_codes_bp.route("/<salary_code>", methods=["PUT"])
def update_salary_code(salary_code):
    """Update salary code"""
    try:
        wage = WageMaster.query.filter_by(salary_code=salary_code, is_active=True).first()
        if not wage:
            return jsonify({"success": False, "message": "Salary code not found"}), 404

        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()

        # Validate the data
        errors = validate_wage_master_data(payload)
        if errors:
            return jsonify({"success": False, "message": "Validation errors", "errors": errors}), 400

        # Update fields
        wage.site_name = payload.get("site_name", wage.site_name)
        wage.rank = payload.get("rank", wage.rank)
        wage.state = payload.get("state", wage.state)
        wage.base_wage = float(payload.get("base_wage", wage.base_wage))
        wage.skill_level = payload.get("skill_level", wage.skill_level)

        # Regenerate salary code if site/rank/state changed
        new_salary_code = _generate_salary_code(wage.site_name, wage.rank, wage.state)
        if new_salary_code != wage.salary_code:
            wage.salary_code = new_salary_code

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Salary code updated successfully",
            "data": {
                "id": wage.id,
                "salary_code": wage.salary_code,
                "site_name": wage.site_name,
                "rank": wage.rank,
                "state": wage.state,
                "base_wage": wage.base_wage,
                "skill_level": wage.skill_level
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


@salary_codes_bp.route("/<salary_code>", methods=["DELETE"])
def delete_salary_code(salary_code):
    """Soft delete salary code"""
    try:
        wage = WageMaster.query.filter_by(salary_code=salary_code, is_active=True).first()
        if not wage:
            return jsonify({"success": False, "message": "Salary code not found"}), 404

        wage.is_active = False
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Salary code deleted successfully"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400
