from flask import Blueprint, request, jsonify
from services.attendance_service import AttendanceService
from datetime import datetime, date
import json

attendance_bp = Blueprint("attendance", __name__)

@attendance_bp.route("/mark", methods=["POST"])
def mark_attendance():
    """
    Mark attendance for an employee

    Expected JSON payload:
    {
        "employee_id": "EMP001",
        "attendance_date": "2024-01-15",  # Optional, defaults to today
        "attendance_status": "Present",   # Present, Absent, Late, Half Day
        "check_in_time": "2024-01-15T09:00:00",  # Optional
        "check_out_time": "2024-01-15T17:00:00", # Optional
        "overtime_hours": 2.0,            # Optional
        "remarks": "Working on project",  # Optional
        "marked_by": "employee"           # Optional, defaults to 'employee'
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Required fields
        employee_id = data.get('employee_id')
        if not employee_id:
            return jsonify({"success": False, "message": "Employee ID is required"}), 400

        # Optional fields with defaults
        attendance_date = data.get('attendance_date', date.today().isoformat())
        attendance_status = data.get('attendance_status', 'Present')
        marked_by = data.get('marked_by', 'employee')

        # Parse datetime fields if provided
        check_in_time = None
        check_out_time = None

        if data.get('check_in_time'):
            check_in_time = datetime.fromisoformat(data['check_in_time'].replace('Z', '+00:00'))

        if data.get('check_out_time'):
            check_out_time = datetime.fromisoformat(data['check_out_time'].replace('Z', '+00:00'))

        # Mark attendance
        result = AttendanceService.mark_attendance(
            employee_id=employee_id,
            attendance_date=attendance_date,
            attendance_status=attendance_status,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            overtime_hours=data.get('overtime_hours', 0.0),
            remarks=data.get('remarks'),
            marked_by=marked_by
        )

        if result["success"]:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error marking attendance: {str(e)}"
        }), 500

@attendance_bp.route("/bulk-mark", methods=["POST"])
def bulk_mark_attendance():
    """
    Mark attendance for multiple employees

    Expected JSON payload:
    {
        "attendance_records": [
            {
                "employee_id": "EMP001",
                "attendance_date": "2024-01-15",
                "attendance_status": "Present",
                "check_in_time": "2024-01-15T09:00:00",
                "check_out_time": "2024-01-15T17:00:00",
                "overtime_hours": 0.0,
                "remarks": ""
            },
            // ... more records
        ],
        "marked_by": "admin"
    }
    """
    try:
        data = request.get_json()

        if not data or not data.get('attendance_records'):
            return jsonify({
                "success": False,
                "message": "No attendance records provided"
            }), 400

        attendance_records = data['attendance_records']
        marked_by = data.get('marked_by', 'admin')

        # Process datetime fields for each record
        for record in attendance_records:
            if record.get('check_in_time'):
                record['check_in_time'] = datetime.fromisoformat(
                    record['check_in_time'].replace('Z', '+00:00')
                )

            if record.get('check_out_time'):
                record['check_out_time'] = datetime.fromisoformat(
                    record['check_out_time'].replace('Z', '+00:00')
                )

        result = AttendanceService.bulk_mark_attendance(attendance_records, marked_by)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in bulk attendance marking: {str(e)}"
        }), 500

@attendance_bp.route("/employee/<employee_id>", methods=["GET"])
def get_employee_attendance(employee_id):
    """
    Get attendance records for a specific employee

    Query parameters:
    - start_date: YYYY-MM-DD (optional)
    - end_date: YYYY-MM-DD (optional)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        result = AttendanceService.get_employee_attendance(
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date
        )

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching employee attendance: {str(e)}"
        }), 500

@attendance_bp.route("/date/<attendance_date>", methods=["GET"])
def get_attendance_by_date(attendance_date):
    """
    Get all attendance records for a specific date

    URL parameter:
    - attendance_date: YYYY-MM-DD
    """
    try:
        result = AttendanceService.get_attendance_by_date(attendance_date)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching attendance by date: {str(e)}"
        }), 500

@attendance_bp.route("/monthly-summary/<employee_id>", methods=["GET"])
def get_monthly_attendance_summary(employee_id):
    """
    Get monthly attendance summary for salary calculation

    Query parameters:
    - year: YYYY (required)
    - month: MM (required)
    """
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)

        if not year or not month:
            return jsonify({
                "success": False,
                "message": "Year and month are required parameters"
            }), 400

        if month < 1 or month > 12:
            return jsonify({
                "success": False,
                "message": "Month must be between 1 and 12"
            }), 400

        result = AttendanceService.get_monthly_attendance_summary(
            employee_id=employee_id,
            year=year,
            month=month
        )

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching monthly summary: {str(e)}"
        }), 500

@attendance_bp.route("/update/<attendance_id>", methods=["PUT"])
def update_attendance(attendance_id):
    """
    Update existing attendance record

    Expected JSON payload:
    {
        "attendance_status": "Present",
        "check_in_time": "2024-01-15T09:00:00",
        "check_out_time": "2024-01-15T17:00:00",
        "overtime_hours": 2.0,
        "remarks": "Updated remarks",
        "is_approved": true,
        "approved_by": "admin",
        "updated_by": "admin"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        # Parse datetime fields if provided
        if data.get('check_in_time'):
            data['check_in_time'] = datetime.fromisoformat(
                data['check_in_time'].replace('Z', '+00:00')
            )

        if data.get('check_out_time'):
            data['check_out_time'] = datetime.fromisoformat(
                data['check_out_time'].replace('Z', '+00:00')
            )

        result = AttendanceService.update_attendance(attendance_id, **data)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error updating attendance: {str(e)}"
        }), 500

@attendance_bp.route("/today", methods=["GET"])
def get_today_attendance():
    """
    Get all attendance records for today
    """
    try:
        today = date.today().isoformat()
        result = AttendanceService.get_attendance_by_date(today)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching today's attendance: {str(e)}"
        }), 500