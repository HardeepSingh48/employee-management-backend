from flask import Blueprint, request, jsonify, url_for
from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.site import Site
from models.wage_master import WageMaster
from routes.auth import token_required
from services.attendance_service import AttendanceService
from services.salary_service import SalaryService
from datetime import datetime, date, timedelta
from sqlalchemy import and_, func, desc
import calendar
import os

from config import ATTENDANCE_UPLOADS_DIR
from utils.geofence import calculate_distance

employee_dashboard_bp = Blueprint("employee_dashboard", __name__)


def _resolve_employee_site(employee: Employee, current_user) -> Site | None:
    """Resolve the most reliable site association for the current employee."""
    if current_user.role == 'supervisor' and getattr(current_user, 'site_id', None):
        site = Site.query.get(current_user.site_id)
        if site:
            return site

    if employee.site:
        return employee.site

    if employee.site_id:
        site = Site.query.get(employee.site_id)
        if site:
            return site

    if employee.wage_master and employee.wage_master.site_id:
        site = Site.query.get(employee.wage_master.site_id)
        if site:
            return site

    if employee.wage_master and employee.wage_master.site_name:
        return Site.query.filter(func.lower(Site.site_name) == employee.wage_master.site_name.strip().lower()).first()

    return None


def _format_full_name(first_name: str | None, last_name: str | None) -> str:
    full_name = f"{first_name or ''} {last_name or ''}".strip()
    return full_name or 'Unknown Employee'


def _parse_month_range() -> tuple[date, date, int, int]:
    month_param = request.args.get('month')
    year_param = request.args.get('year', type=int)

    if month_param and '-' in month_param:
        year_str, month_str = month_param.split('-', 1)
        year = int(year_str)
        month = int(month_str)
    else:
        month = request.args.get('month', datetime.now().month, type=int)
        year = year_param or datetime.now().year

    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    return start_date, end_date, year, month


def _build_attendance_media_url(employee_id: int, selfie_photo_url: str | None) -> str | None:
    if not selfie_photo_url:
        return None

    if selfie_photo_url.startswith('http://') or selfie_photo_url.startswith('https://'):
        return selfie_photo_url

    filename = os.path.basename(selfie_photo_url)
    return url_for('media.get_attendance_photo', employee_id=employee_id, filename=filename, _external=True)


def _build_profile_payload(current_user, employee: Employee) -> dict:
    site = _resolve_employee_site(employee, current_user)
    department_name = employee.department.department_name if employee.department else employee.department_id
    full_name = _format_full_name(employee.first_name, employee.last_name)

    return {
        'employee_id': employee.employee_id,
        'first_name': employee.first_name,
        'last_name': employee.last_name,
        'full_name': full_name,
        'designation': employee.designation,
        'job_title': employee.job_title,
        'site_name': site.site_name if site else None,
        'site_id': site.site_id if site else employee.site_id,
        'department': department_name,
        'employment_type': employee.employment_type,
        'phone_number': employee.phone_number,
        'email': employee.email,
        'hire_date': employee.hire_date.isoformat() if employee.hire_date else None,
    }


def _serialise_attendance_record(record: Attendance) -> dict:
    return {
        'attendance_id': record.attendance_id,
        'attendance_date': record.attendance_date.isoformat() if record.attendance_date else None,
        'attendance_status': record.attendance_status,
        'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
        'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
        'overtime_shifts': record.overtime_shifts,
        'overtime_hours': record.overtime_hours,
        'selfie_photo_url': _build_attendance_media_url(record.employee_id, record.selfie_photo_url),
        'check_in_latitude': record.check_in_latitude,
        'check_in_longitude': record.check_in_longitude,
        'gps_accuracy_metres': record.gps_accuracy_metres,
        'is_within_geofence': record.is_within_geofence,
        'attendance_source': record.attendance_source,
        'fraud_flags': record.fraud_flags or [],
        'verification_status': record.verification_status,
        'remarks': record.remarks,
        'marked_by': record.marked_by,
        'late_minutes': record.late_minutes,
        'early_departure_minutes': record.early_departure_minutes,
        'total_hours_worked': record.total_hours_worked,
        'created_date': record.created_date.isoformat() if record.created_date else None,
    }


def _build_history_summary(records: list[Attendance]) -> dict:
    present = sum(1 for record in records if record.attendance_status == 'Present')
    absent = sum(1 for record in records if record.attendance_status == 'Absent')
    off = sum(1 for record in records if record.attendance_status == 'OFF')
    overtime_shifts = round(sum(record.effective_overtime_shifts for record in records), 2)

    return {
        'present': present,
        'absent': absent,
        'off': off,
        'overtime_shifts': overtime_shifts,
    }


def _save_attendance_photo(photo_file, employee_id: int, attendance_date: date) -> str:
    employee_folder = os.path.join(ATTENDANCE_UPLOADS_DIR, str(employee_id))
    os.makedirs(employee_folder, exist_ok=True)

    filename = f"{attendance_date.isoformat()}_checkin.jpg"
    file_path = os.path.join(employee_folder, filename)
    photo_file.save(file_path)
    return f"/api/media/attendance/{employee_id}/{filename}"

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

        profile_data = _build_profile_payload(current_user, employee)

        return jsonify({
            "success": True,
            "data": {
                **profile_data,
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
                'salary_info': {
                    'salary_code': employee.wage_master.salary_code if employee.wage_master else None,
                    'site_name': employee.wage_master.site_name if employee.wage_master else None,
                    'rank': employee.wage_master.rank if employee.wage_master else None,
                    'state': employee.wage_master.state if employee.wage_master else None,
                    'base_wage': employee.wage_master.base_wage if employee.wage_master else None,
                    'skill_level': employee.wage_master.skill_level if employee.wage_master else None
                }
            }
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
        result = AttendanceService.mark_or_update_attendance(
            employee_id=current_user.employee_id,
            attendance_date=attendance_date,
            attendance_status=attendance_status,
            check_in_time=check_in_datetime,
            check_out_time=check_out_datetime,
            overtime_shifts=overtime_hours,
            remarks=remarks,
            marked_by='employee'
        )
        
        return jsonify(result), 201 if result['success'] else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error marking attendance: {str(e)}"
        }), 500


@employee_dashboard_bp.route("/site-config", methods=["GET"])
@token_required
def get_site_config(current_user):
    """Return the resolved site configuration for the current employee."""
    try:
        if not current_user.employee_id or not current_user.employee:
            return jsonify({"success": False, "message": "No employee record found for this user"}), 404

        site = _resolve_employee_site(current_user.employee, current_user)
        if not site:
            return jsonify({"success": False, "message": "No site configuration found for this employee"}), 404

        return jsonify({
            "success": True,
            "data": {
                "site_id": site.site_id,
                "site_name": site.site_name,
                "latitude": site.latitude,
                "longitude": site.longitude,
                "radius_metres": site.radius_metres or 200,
            }
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "message": f"Error getting site config: {exc}"}), 500


@employee_dashboard_bp.route("/attendance/today", methods=["GET"])
@token_required
def get_today_attendance(current_user):
    """Return the authenticated employee's attendance for today."""
    try:
        if not current_user.employee_id:
            return jsonify({"success": False, "message": "No employee record found for this user"}), 404

        today_record = Attendance.query.filter_by(
            employee_id=current_user.employee_id,
            attendance_date=date.today(),
        ).first()

        return jsonify({
            "success": True,
            "data": {
                "checked_in": bool(today_record and today_record.check_in_time),
                "check_in_time": today_record.check_in_time.isoformat() if today_record and today_record.check_in_time else None,
                "attendance_status": today_record.attendance_status if today_record else None,
                "verification_status": today_record.verification_status if today_record else None,
            }
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "message": f"Error getting today's attendance: {exc}"}), 500


@employee_dashboard_bp.route("/attendance/geo-checkin", methods=["POST"])
@token_required
def geo_checkin(current_user):
    """Capture a selfie-based geofence attendance check-in."""
    try:
        if not current_user.employee_id or not current_user.employee:
            return jsonify({"success": False, "message": "No employee record found for this user"}), 404

        photo_file = request.files.get('selfie')
        if photo_file is None:
            return jsonify({"success": False, "message": "Selfie image is required"}), 400

        latitude_raw = request.form.get('latitude')
        longitude_raw = request.form.get('longitude')
        accuracy_raw = request.form.get('gps_accuracy')
        is_mocked_raw = request.form.get('is_mocked', 'false').strip().lower()
        device_id = request.form.get('device_id', '').strip()

        if not latitude_raw or not longitude_raw or not accuracy_raw:
            return jsonify({"success": False, "message": "Latitude, longitude and gps_accuracy are required"}), 400

        latitude = float(latitude_raw)
        longitude = float(longitude_raw)
        gps_accuracy = float(accuracy_raw)
        is_mocked = is_mocked_raw == 'true'

        if not current_user.device_id:
            return jsonify({"success": False, "message": "No registered device found for this account", "fraud_flags": ["unregistered_device"]}), 403

        if device_id != current_user.device_id:
            return jsonify({"success": False, "message": "Device verification failed", "fraud_flags": ["device_mismatch"]}), 403

        if is_mocked:
            return jsonify({"success": False, "message": "Mock location detected", "fraud_flags": ["mock_location"]}), 403

        site = _resolve_employee_site(current_user.employee, current_user)
        if not site or site.latitude is None or site.longitude is None:
            return jsonify({"success": False, "message": "Employee site geofence is not configured"}), 400

        distance_metres = calculate_distance(latitude, longitude, float(site.latitude), float(site.longitude))
        is_within_geofence = distance_metres <= float(site.radius_metres or 200)

        fraud_flags: list[str] = []
        if not is_within_geofence:
            fraud_flags.append('outside_geofence')
        if gps_accuracy > 50:
            fraud_flags.append('low_gps_accuracy')

        verification_status = 'auto_approved' if not fraud_flags else 'pending_review'

        attendance_date = date.today()
        existing_record = Attendance.query.filter_by(
            employee_id=current_user.employee_id,
            attendance_date=attendance_date,
        ).first()

        selfie_photo_url = _save_attendance_photo(photo_file, current_user.employee_id, attendance_date)
        now = datetime.utcnow()

        if existing_record is None:
            attendance_record = Attendance(
                employee_id=current_user.employee_id,
                attendance_date=attendance_date,
                check_in_time=now,
                check_out_time=None,
                attendance_status='Present',
                selfie_photo_url=selfie_photo_url,
                check_in_latitude=latitude,
                check_in_longitude=longitude,
                gps_accuracy_metres=gps_accuracy,
                is_within_geofence=is_within_geofence,
                attendance_source='self-mobile',
                fraud_flags=fraud_flags,
                verification_status=verification_status,
                marked_by='employee',
                created_by=current_user.email,
                total_hours_worked=8.0 if is_within_geofence else 0.0,
            )
            db.session.add(attendance_record)
            response_status = 201
        else:
            existing_record.check_in_time = now
            existing_record.attendance_status = 'Present'
            existing_record.selfie_photo_url = selfie_photo_url
            existing_record.check_in_latitude = latitude
            existing_record.check_in_longitude = longitude
            existing_record.gps_accuracy_metres = gps_accuracy
            existing_record.is_within_geofence = is_within_geofence
            existing_record.attendance_source = 'self-mobile'
            existing_record.fraud_flags = fraud_flags
            existing_record.verification_status = verification_status
            existing_record.marked_by = 'employee'
            existing_record.updated_by = current_user.email
            existing_record.updated_date = datetime.utcnow().date()
            attendance_record = existing_record
            response_status = 200

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Check-in submitted successfully",
            "data": {
                **attendance_record.to_dict(),
                "distance_metres": round(distance_metres, 2),
                "is_within_geofence": is_within_geofence,
                "fraud_flags": fraud_flags,
            }
        }), response_status
    except Exception as exc:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error submitting check-in: {exc}"}), 500

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

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 30, type=int)
        start_date, end_date, year, month = _parse_month_range()

        query = Attendance.query.filter_by(employee_id=current_user.employee_id)
        query = query.filter(
            and_(
                Attendance.attendance_date >= start_date,
                Attendance.attendance_date <= end_date,
            )
        )
        query = query.order_by(desc(Attendance.attendance_date))

        all_month_records = query.all()
        attendance_records = query.paginate(page=page, per_page=per_page, error_out=False)
        records = [_serialise_attendance_record(record) for record in attendance_records.items]
        summary = _build_history_summary(all_month_records)

        return jsonify({
            "success": True,
            "data": {
                "records": records,
                "summary": summary,
                "month": f"{year:04d}-{month:02d}",
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
                'late_days': 0,  # Late days are now counted as present days
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
