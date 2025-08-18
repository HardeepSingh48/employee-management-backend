from flask import Blueprint, request, jsonify
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.wage_master import WageMaster
from routes.auth import token_required
from services.attendance_service import AttendanceService
from services.salary_service import SalaryService
from datetime import datetime, date, timedelta
from sqlalchemy import and_, func, desc
import calendar

employee_dashboard_bp = Blueprint("employee_dashboard", __name__)

@employee_dashboard_bp.route("/profile", methods=["GET"])
@token_required
def get_employee_profile(current_user):
    """Get employee profile information"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        employee = current_user.employee
        if not employee:
            return jsonify({
                "success": False,
                "message": "Employee record not found"
            }), 404
        
        # Get salary code details
        salary_code_details = None
        if employee.wage_master:
            salary_code_details = {
                'salary_code': employee.wage_master.salary_code,
                'site_name': employee.wage_master.site_name,
                'rank': employee.wage_master.rank,
                'state': employee.wage_master.state,
                'base_wage': employee.wage_master.base_wage,
                'skill_level': employee.wage_master.skill_level
            }
        
        profile_data = {
            'user_info': current_user.to_dict(),
            'employee_info': {
                'employee_id': employee.employee_id,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'email': employee.email,
                'phone_number': employee.phone_number,
                'address': employee.address,
                'date_of_birth': employee.date_of_birth.isoformat() if employee.date_of_birth else None,
                'hire_date': employee.hire_date.isoformat() if employee.hire_date else None,
                'department_id': employee.department_id,
                'designation': employee.designation,
                'employment_status': employee.employment_status,
                'gender': employee.gender,
                'marital_status': employee.marital_status,
                'blood_group': employee.blood_group,
                'pan_card_number': employee.pan_card_number,
                'adhar_number': employee.adhar_number,
                'uan': employee.uan,
                'esic_number': employee.esic_number
            },
            'salary_info': salary_code_details
        }
        
        return jsonify({
            "success": True,
            "data": profile_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting profile: {str(e)}"
        }), 500

@employee_dashboard_bp.route("/attendance/mark", methods=["POST"])
@token_required
def mark_self_attendance(current_user):
    """Allow employee to mark their own attendance"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        # Use current date if not provided
        attendance_date = data.get('attendance_date', date.today().isoformat())
        attendance_status = data.get('attendance_status', 'Present')
        check_in_time = data.get('check_in_time')
        check_out_time = data.get('check_out_time')
        overtime_hours = data.get('overtime_hours', 0.0)
        remarks = data.get('remarks', '')
        
        # Convert check-in/out times to datetime if provided
        check_in_datetime = None
        check_out_datetime = None
        
        if check_in_time:
            check_in_datetime = datetime.fromisoformat(f"{attendance_date}T{check_in_time}:00")
        
        if check_out_time:
            check_out_datetime = datetime.fromisoformat(f"{attendance_date}T{check_out_time}:00")
        
        # Mark attendance using the service
        result = AttendanceService.mark_attendance(
            employee_id=current_user.employee_id,
            attendance_date=attendance_date,
            attendance_status=attendance_status,
            check_in_time=check_in_datetime,
            check_out_time=check_out_datetime,
            overtime_hours=overtime_hours,
            remarks=remarks,
            marked_by='employee'
        )
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error marking attendance: {str(e)}"
        }), 500

@employee_dashboard_bp.route("/attendance/history", methods=["GET"])
@token_required
def get_attendance_history(current_user):
    """Get employee's attendance history"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 30, type=int)
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        # Build query
        query = Attendance.query.filter_by(employee_id=current_user.employee_id)
        
        # Filter by month/year if provided
        if month and year:
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
            query = query.filter(
                and_(
                    Attendance.attendance_date >= start_date,
                    Attendance.attendance_date <= end_date
                )
            )
        
        # Order by date descending
        query = query.order_by(desc(Attendance.attendance_date))
        
        # Paginate
        attendance_records = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format records
        records = []
        for record in attendance_records.items:
            records.append({
                'attendance_id': record.attendance_id,
                'attendance_date': record.attendance_date.isoformat(),
                'attendance_status': record.attendance_status,
                'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                'total_hours_worked': record.total_hours_worked,
                'overtime_hours': record.overtime_hours,
                'late_minutes': record.late_minutes,
                'is_holiday': record.is_holiday,
                'is_weekend': record.is_weekend,
                'remarks': record.remarks,
                'marked_by': record.marked_by,
                'created_date': record.created_date.isoformat() if record.created_date else None
            })
        
        return jsonify({
            "success": True,
            "data": {
                "records": records,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": attendance_records.total,
                    "pages": attendance_records.pages,
                    "has_next": attendance_records.has_next,
                    "has_prev": attendance_records.has_prev
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting attendance history: {str(e)}"
        }), 500

@employee_dashboard_bp.route("/attendance/summary", methods=["GET"])
@token_required
def get_attendance_summary(current_user):
    """Get employee's attendance summary for current month"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        # Get month/year from query params or use current
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Get monthly summary using attendance service
        result = AttendanceService.get_monthly_attendance_summary(
            current_user.employee_id, year, month
        )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting attendance summary: {str(e)}"
        }), 500

@employee_dashboard_bp.route("/salary/current", methods=["GET"])
@token_required
def get_current_salary(current_user):
    """Get employee's current month salary calculation"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        # Get month/year from query params or use current
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        
        # Calculate individual salary
        result = SalaryService.calculate_individual_salary(
            current_user.employee_id, year, month
        )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error calculating salary: {str(e)}"
        }), 500

@employee_dashboard_bp.route("/dashboard/stats", methods=["GET"])
@token_required
def get_dashboard_stats(current_user):
    """Get dashboard statistics for employee"""
    try:
        if not current_user.employee_id:
            return jsonify({
                "success": False,
                "message": "No employee record found for this user"
            }), 404
        
        # Current month stats
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Get attendance summary for current month
        attendance_summary = AttendanceService.get_monthly_attendance_summary(
            current_user.employee_id, current_year, current_month
        )
        
        # Get today's attendance
        today = date.today()
        today_attendance = Attendance.query.filter_by(
            employee_id=current_user.employee_id,
            attendance_date=today
        ).first()
        
        # Calculate working days in current month
        working_days = 0
        for day in range(1, calendar.monthrange(current_year, current_month)[1] + 1):
            check_date = date(current_year, current_month, day)
            if check_date.weekday() < 6:  # Monday = 0, Sunday = 6
                working_days += 1
        
        stats = {
            'today_status': {
                'date': today.isoformat(),
                'marked': today_attendance is not None,
                'status': today_attendance.attendance_status if today_attendance else None,
                'check_in': today_attendance.check_in_time.strftime('%H:%M') if today_attendance and today_attendance.check_in_time else None,
                'check_out': today_attendance.check_out_time.strftime('%H:%M') if today_attendance and today_attendance.check_out_time else None
            },
            'monthly_stats': {
                'month': current_month,
                'year': current_year,
                'working_days': working_days,
                'present_days': attendance_summary.get('data', {}).get('present_days', 0) if attendance_summary.get('success') else 0,
                'absent_days': attendance_summary.get('data', {}).get('absent_days', 0) if attendance_summary.get('success') else 0,
                'late_days': attendance_summary.get('data', {}).get('late_days', 0) if attendance_summary.get('success') else 0,
                'attendance_percentage': attendance_summary.get('data', {}).get('attendance_percentage', 0) if attendance_summary.get('success') else 0
            }
        }
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error getting dashboard stats: {str(e)}"
        }), 500
