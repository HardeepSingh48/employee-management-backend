from flask import Blueprint, request, jsonify
from models import db
from models.department import Department

departments_bp = Blueprint("departments", __name__)

@departments_bp.route("/", methods=["GET"])
def list_departments():
    """List all active departments"""
    try:
        departments = Department.query.filter_by(is_active=True).all()
        
        department_list = []
        for dept in departments:
            department_list.append({
                "department_id": dept.department_id,
                "department_name": dept.department_name,
                "description": dept.description,
                "is_active": dept.is_active,
                "created_date": dept.created_date.isoformat() if dept.created_date else None
            })
        
        return jsonify({
            "success": True,
            "data": department_list,
            "count": len(department_list)
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@departments_bp.route("/", methods=["POST"])
def create_department():
    """Create a new department"""
    try:
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()

        # Validate required fields
        if not payload.get("department_id"):
            return jsonify({"success": False, "message": "department_id is required"}), 400
        
        if not payload.get("department_name"):
            return jsonify({"success": False, "message": "department_name is required"}), 400

        # Check if department already exists
        existing_dept = Department.query.filter_by(department_id=payload["department_id"]).first()
        if existing_dept:
            return jsonify({"success": False, "message": "Department with this ID already exists"}), 400

        department = Department(
            department_id=payload["department_id"],
            department_name=payload["department_name"],
            description=payload.get("description"),
            created_by=payload.get("created_by", "system")
        )
        
        db.session.add(department)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Department created successfully",
            "data": {
                "department_id": department.department_id,
                "department_name": department.department_name,
                "description": department.description
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 400


@departments_bp.route("/<department_id>", methods=["GET"])
def get_department(department_id):
    """Get department by ID"""
    try:
        department = Department.query.filter_by(department_id=department_id, is_active=True).first()
        if not department:
            return jsonify({"success": False, "message": "Department not found"}), 404
        
        return jsonify({
            "success": True,
            "data": {
                "department_id": department.department_id,
                "department_name": department.department_name,
                "description": department.description,
                "is_active": department.is_active,
                "created_date": department.created_date.isoformat() if department.created_date else None
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
