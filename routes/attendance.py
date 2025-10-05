from flask import Blueprint, request, jsonify,send_file
from services.attendance_service import AttendanceService
from models import db
from models.employee import Employee
from models.attendance import Attendance
from datetime import datetime, date, timedelta
import json
import pandas as pd
from io import BytesIO
from routes.auth import token_required
import logging
import os
import calendar
import time
import uuid
from utils.attendance_helpers import round_to_half, normalize_attendance_value, is_date, parse_date_from_column

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

attendance_bp = Blueprint("attendance", __name__)

def batch_load_employees(employee_ids, site_id=None, user_role='admin'):
    """Load employees in batch with site filtering through salary codes"""
    if user_role == 'supervisor' and site_id:
        # For supervisors, filter by site through salary code relationships
        from models.wage_master import WageMaster
        from models.site import Site
        query = Employee.query.join(
            WageMaster, Employee.salary_code == WageMaster.salary_code
        ).join(
            Site, WageMaster.site_name == Site.site_name
        ).filter(
            Employee.employee_id.in_(employee_ids),
            Site.site_id == site_id
        )
    else:
        # For admins or when no site filtering, just filter by employee IDs
        query = Employee.query.filter(Employee.employee_id.in_(employee_ids))

    employees = query.all()
    return {str(emp.employee_id).strip(): emp for emp in employees}

def batch_load_existing_attendance(employee_ids, start_date, end_date):
    """Load existing attendance records in batch"""
    existing_attendance = Attendance.query.filter(
        Attendance.employee_id.in_(employee_ids),
        Attendance.attendance_date >= start_date,
        Attendance.attendance_date <= end_date
    ).all()
    
    # Create lookup dictionary: "employee_id_date" -> attendance_record
    existing_dict = {}
    for att in existing_attendance:
        key = f"{att.employee_id}_{att.attendance_date}"
        existing_dict[key] = att
    
    return existing_dict

def safe_bulk_insert(attendance_dicts, chunk_size=1000):
    """Safely insert attendance records in chunks"""
    results = {
        "successful": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        # Process in chunks to avoid memory issues
        for i in range(0, len(attendance_dicts), chunk_size):
            chunk = attendance_dicts[i:i + chunk_size]
            try:
                db.session.bulk_insert_mappings(Attendance, chunk)
                db.session.flush()
                results["successful"] += len(chunk)
                logger.info(f"Successfully processed chunk {i//chunk_size + 1}: {len(chunk)} records")
            except Exception as chunk_error:
                db.session.rollback()
                logger.error(f"Chunk {i//chunk_size + 1} failed: {str(chunk_error)}")
                
                # Fallback: Try individual inserts for failed chunk
                for record in chunk:
                    try:
                        attendance = Attendance(**record)
                        db.session.add(attendance)
                        db.session.flush()
                        results["successful"] += 1
                    except Exception as individual_error:
                        db.session.rollback()
                        results["failed"] += 1
                        results["errors"].append(
                            f"Employee {record.get('employee_id', 'Unknown')}: {str(individual_error)}"
                        )
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk insert failed: {str(e)}")
        results["errors"].append(f"Bulk operation failed: {str(e)}")
        raise e
    
    return results


def safe_read_excel(file_storage, **kwargs):
    """
    Safely read Excel file with multiple engine attempts
    """
    engines = ['openpyxl', 'xlrd']
    
    for engine in engines:
        try:
            # Reset file pointer
            file_storage.seek(0)
            return pd.read_excel(file_storage, engine=engine, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to read with engine {engine}: {str(e)}")
            continue
    
    # If all engines fail, try without specifying engine
    try:
        file_storage.seek(0)
        return pd.read_excel(file_storage, **kwargs)
    except Exception as e:
        logger.error(f"Failed to read Excel file with any engine: {str(e)}")
        raise ValueError(f"Unable to read Excel file. Please ensure it's a valid Excel file (.xlsx or .xls). Error: {str(e)}")


@attendance_bp.route("/mark", methods=["POST"])
@token_required
def mark_attendance(current_user):
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

        # Role-based validation
        today = date.today()

        if current_user.role == 'employee':
            # Employees can only mark their own attendance for today
            if employee_id != current_user.employee_id:
                return jsonify({"success": False, "message": "Employees can only mark their own attendance"}), 403

            # Employees can only mark for today
            try:
                requested_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
                if requested_date != today:
                    return jsonify({
                        "success": False,
                        "message": "Employees can only mark attendance for the current day"
                    }), 403
            except ValueError:
                return jsonify({"success": False, "message": "Invalid date format"}), 400

        elif current_user.role == 'supervisor':
            # Supervisors can only mark attendance for employees in their site
            from models.wage_master import WageMaster
            from models.site import Site
            employee = Employee.query.join(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).join(
                Site, WageMaster.site_name == Site.site_name
            ).filter(
                Employee.employee_id == employee_id,
                Site.site_id == current_user.site_id
            ).first()
            if not employee:
                return jsonify({"success": False, "message": "Employee not found or not in your site"}), 403

            # Supervisors can mark for current day and previous 3 days
            try:
                requested_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()
                min_allowed_date = today - timedelta(days=3)

                if requested_date < min_allowed_date or requested_date > today:
                    return jsonify({
                        "success": False,
                        "message": "Supervisors can only mark attendance for the current day and the previous 3 days"
                    }), 403
            except ValueError:
                return jsonify({"success": False, "message": "Invalid date format"}), 400

        # Admins have no restrictions - they can mark any date for any employee
        attendance_status = data.get('attendance_status', 'Present')
        marked_by = current_user.role if current_user.role in ['supervisor', 'admin'] else 'employee'

        # Parse datetime fields if provided
        check_in_time = None
        check_out_time = None

        if data.get('check_in_time'):
            check_in_time = datetime.fromisoformat(data['check_in_time'].replace('Z', '+00:00'))

        if data.get('check_out_time'):
            check_out_time = datetime.fromisoformat(data['check_out_time'].replace('Z', '+00:00'))

        # Handle overtime data with backward compatibility
        overtime_shifts = 0.0
        
        # Check for overtime_shifts first (new format)
        if 'overtime_shifts' in data:
            overtime_shifts = float(data['overtime_shifts'])
        # Backward compatibility: if overtime_hours is present, convert to shifts
        elif 'overtime_hours' in data:
            overtime_hours = float(data['overtime_hours'])
            overtime_shifts = round_to_half(overtime_hours / 8.0)
        
        # Validate overtime_shifts
        if overtime_shifts < 0:
            return jsonify({"success": False, "message": "Overtime shifts cannot be negative"}), 400
        
        # Round to nearest 0.5 if not already
        overtime_shifts = round_to_half(overtime_shifts)
        
        # Mark attendance
        result = AttendanceService.mark_attendance(
            employee_id=employee_id,
            attendance_date=attendance_date,
            attendance_status=attendance_status,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            overtime_shifts=overtime_shifts,
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
@token_required
def bulk_mark_attendance(current_user):
    """
    Mark attendance for multiple employees (supervisor only)
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        data = request.get_json()

        if not data or not data.get('attendance_records'):
            return jsonify({
                "success": False,
                "message": "No attendance records provided"
            }), 400

        attendance_records = data['attendance_records']
        marked_by = current_user.role

        # Role-based validation for bulk operations
        today = date.today()

        if current_user.role == 'employee':
            # Employees cannot perform bulk operations
            return jsonify({"success": False, "message": "Employees cannot perform bulk attendance operations"}), 403

        elif current_user.role == 'supervisor':
            # Supervisors can only mark attendance for employees in their site
            from models.wage_master import WageMaster
            from models.site import Site

            min_allowed_date = today - timedelta(days=3)

            for record in attendance_records:
                # Validate date range for supervisors
                if record.get('attendance_date'):
                    try:
                        requested_date = datetime.strptime(record['attendance_date'], '%Y-%m-%d').date()
                        if requested_date < min_allowed_date or requested_date > today:
                            return jsonify({
                                "success": False,
                                "message": f"Supervisors can only mark attendance for the current day and the previous 3 days. Date {record['attendance_date']} is not allowed."
                            }), 403
                    except ValueError:
                        return jsonify({"success": False, "message": f"Invalid date format for employee {record.get('employee_id')}"}), 400

                employee = Employee.query.join(
                    WageMaster, Employee.salary_code == WageMaster.salary_code
                ).join(
                    Site, WageMaster.site_name == Site.site_name
                ).filter(
                    Employee.employee_id == record.get('employee_id'),
                    Site.site_id == current_user.site_id
                ).first()
                if not employee:
                    return jsonify({
                        "success": False,
                        "message": f"Employee {record.get('employee_id')} not found or not in your site"
                    }), 403

        # Admins have no restrictions for bulk operations

        # Process datetime fields and overtime data for each record
        for record in attendance_records:
            if record.get('check_in_time'):
                record['check_in_time'] = datetime.fromisoformat(
                    record['check_in_time'].replace('Z', '+00:00')
                )

            if record.get('check_out_time'):
                record['check_out_time'] = datetime.fromisoformat(
                    record['check_out_time'].replace('Z', '+00:00')
                )
            
            # Handle overtime data with backward compatibility
            overtime_shifts = 0.0
            
            # Check for overtime_shifts first (new format)
            if 'overtime_shifts' in record:
                overtime_shifts = float(record['overtime_shifts'])
            # Backward compatibility: if overtime_hours is present, convert to shifts
            elif 'overtime_hours' in record:
                overtime_hours = float(record['overtime_hours'])
                overtime_shifts = round_to_half(overtime_hours / 8.0)
            
            # Validate overtime_shifts
            if overtime_shifts < 0:
                return jsonify({"success": False, "message": f"Overtime shifts cannot be negative for employee {record.get('employee_id')}"}), 400
            
            # Round to nearest 0.5 if not already
            overtime_shifts = round_to_half(overtime_shifts)
            record['overtime_shifts'] = overtime_shifts

        result = AttendanceService.bulk_mark_attendance(attendance_records, marked_by)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error in bulk attendance marking: {str(e)}"
        }), 500

@attendance_bp.route("/site-employees", methods=["GET"])
@token_required
def get_site_employees(current_user):
    """
    Get employees for supervisor's site with pagination
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 200)
    - search: Search term for employee name or ID
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)  # Max 200 per page
        search = request.args.get('search', '').strip()

        # Base query
        query = Employee.query

        # Apply role-based filtering
        if current_user.role == 'supervisor':
            # For supervisors, filter by their assigned site through salary codes
            from models.wage_master import WageMaster
            from models.site import Site
            query = query.join(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).join(
                Site, WageMaster.site_name == Site.site_name
            ).filter(Site.site_id == current_user.site_id)
        # For admins, no additional filtering needed

        # Apply search filter if provided
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    Employee.employee_id.ilike(search_filter),
                    Employee.first_name.ilike(search_filter),
                    Employee.last_name.ilike(search_filter)
                )
            )

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination
        employees = query.offset((page - 1) * per_page).limit(per_page).all()

        # Format employee data
        employee_data = []
        for emp in employees:
            # Ensure full_name is never empty
            first_name = emp.first_name or ""
            last_name = emp.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            if not full_name:
                full_name = emp.employee_id  # Fallback to employee ID if no name

            employee_data.append({
                'employee_id': emp.employee_id,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'full_name': full_name,
                'site_id': emp.site_id,
                'department_name': emp.department.department_name if emp.department else None,
                'designation': emp.designation
            })

        response = jsonify({
            "success": True,
            "data": employee_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        })

        # Add caching headers for better performance
        response.headers['Cache-Control'] = 'private, max-age=300'  # Cache for 5 minutes
        response.headers['X-Total-Count'] = str(total_count)

        return response, 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching site employees: {str(e)}"
        }), 500

@attendance_bp.route("/site-attendance", methods=["GET"])
@token_required
def get_site_attendance(current_user):
    """
    Get attendance records for supervisor's site with filtering and pagination
    Query parameters:
    - start_date: Start date filter (YYYY-MM-DD)
    - end_date: End date filter (YYYY-MM-DD)
    - employee_id: Filter by specific employee
    - site_id: Filter by site (admin only)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 100, max: 500)
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        site_id = request.args.get('site_id')

        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 100, type=int), 500)  # Max 500 per page

        # Build query with optimized joins
        query = Attendance.query.join(Employee)

        if current_user.role == 'supervisor':
            # For supervisors, filter by their assigned site through salary codes
            from models.wage_master import WageMaster
            from models.site import Site
            query = query.join(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).join(
                Site, WageMaster.site_name == Site.site_name
            ).filter(Site.site_id == current_user.site_id)
        else:
            # Admin: optionally filter by provided site_id through salary codes
            if site_id:
                from models.wage_master import WageMaster
                from models.site import Site
                query = query.join(
                    WageMaster, Employee.salary_code == WageMaster.salary_code
                ).join(
                    Site, WageMaster.site_name == Site.site_name
                ).filter(Site.site_id == site_id)

        # Apply filters
        if start_date:
            query = query.filter(Attendance.attendance_date >= start_date)

        if end_date:
            query = query.filter(Attendance.attendance_date <= end_date)

        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)

        # Get total count for pagination
        total_count = query.count()

        # Apply pagination and ordering
        attendance_records = query.order_by(Attendance.attendance_date.desc()).offset((page - 1) * per_page).limit(per_page).all()

        # Format results with optimized field selection
        results = []
        for record in attendance_records:
            results.append({
                'attendance_id': record.attendance_id,
                'employee_id': record.employee_id,
                'employee_name': f"{record.employee.first_name or ''} {record.employee.last_name or ''}".strip() or record.employee_id,
                'attendance_date': record.attendance_date.isoformat(),
                'attendance_status': record.attendance_status,
                'overtime_shifts': record.overtime_shifts,
                'remarks': record.remarks,
                'marked_by': record.marked_by,
                # Only include time fields if they exist to reduce payload
                'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                'total_hours_worked': record.total_hours_worked
            })

        response = jsonify({
            "success": True,
            "data": results,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": (total_count + per_page - 1) // per_page
            }
        })

        # Add caching headers (shorter cache for attendance data)
        response.headers['Cache-Control'] = 'private, max-age=60'  # Cache for 1 minute
        response.headers['X-Total-Count'] = str(total_count)

        return response, 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching site attendance: {str(e)}"
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
            response = jsonify(result)
            # Add caching headers for monthly attendance data (cache for 5 minutes)
            # Monthly data doesn't change frequently, so caching is safe
            response.headers['Cache-Control'] = 'private, max-age=300'  # 5 minutes
            response.headers['X-Performance-Optimized'] = 'true'
            return response, 200
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
        
        # Handle overtime data with backward compatibility
        if 'overtime_shifts' in data:
            overtime_shifts = float(data['overtime_shifts'])
            if overtime_shifts < 0:
                return jsonify({"success": False, "message": "Overtime shifts cannot be negative"}), 400
            overtime_shifts = round_to_half(overtime_shifts)
            data['overtime_shifts'] = overtime_shifts
        elif 'overtime_hours' in data:
            overtime_hours = float(data['overtime_hours'])
            overtime_shifts = round_to_half(overtime_hours / 8.0)
            data['overtime_shifts'] = overtime_shifts
            # Remove overtime_hours from data to avoid confusion
            data.pop('overtime_hours', None)

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


@attendance_bp.route("/bulk-upload", methods=["POST"])
@token_required
def bulk_upload_attendance(current_user):
    """Bulk upload attendance via Excel file (supervisor only)"""
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"}), 400
    
    try:
        # Read Excel file
        df = pd.read_excel(BytesIO(file.read()))
        
        # Validate required columns
        required_columns = ['Employee ID', 'Employee Name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                "success": False, 
                "message": f"Missing required columns: {', '.join(missing_columns)}"
            }), 400
        
        # Process attendance data
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for _, row in df.iterrows():
            try:
                employee_id = row['Employee ID']
                
                # Check if employee exists and belongs to supervisor's site
                employee = Employee.query.filter_by(employee_id=employee_id).first()
                if not employee:
                    results["errors"].append(f"Employee {employee_id} not found")
                    results["failed"] += 1
                    continue
                
                # For supervisors, check if employee belongs to their site through salary codes
                if current_user.role == 'supervisor':
                    from models.wage_master import WageMaster
                    from models.site import Site
                    site_check = Employee.query.join(
                        WageMaster, Employee.salary_code == WageMaster.salary_code
                    ).join(
                        Site, WageMaster.site_name == Site.site_name
                    ).filter(
                        Employee.employee_id == employee_id,
                        Site.site_id == current_user.site_id
                    ).first()
                    if not site_check:
                        results["errors"].append(f"Employee {employee_id} not in your site")
                        results["failed"] += 1
                        continue
                
                # Process attendance for each day column
                for col in df.columns:
                    if col.startswith(('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')):
                        if pd.notna(row[col]) and row[col] != '':
                            # Extract date from column name and create attendance record
                            attendance_status = str(row[col]).strip()
                            
                            # You'll need to implement date parsing logic based on your Excel format
                            # For now, using today's date as example
                            attendance_date = date.today()
                            
                            # Check if attendance already exists
                            existing = Attendance.query.filter_by(
                                employee_id=employee.employee_id,
                                attendance_date=attendance_date
                            ).first()
                            
                            if not existing:
                                attendance = Attendance(
                                    employee_id=employee.employee_id,
                                    attendance_date=attendance_date,
                                    attendance_status=attendance_status,
                                    marked_by='supervisor',
                                    created_by=current_user.email
                                )
                                db.session.add(attendance)
                
                results["successful"] += 1
                results["processed"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error processing employee {row.get('Employee ID', 'Unknown')}: {str(e)}")
                results["failed"] += 1
                results["processed"] += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Bulk attendance upload completed",
            "results": results
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Error processing file: {str(e)}"
        }), 500

@attendance_bp.route("/template", methods=["GET"])
@token_required
def download_attendance_template(current_user):
    if current_user.role not in ['supervisor', 'admin', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    # Optional filters from frontend
    month_param = request.args.get('month', type=int)
    year_param = request.args.get('year', type=int)
    site_param = request.args.get('site_id', type=str)
    logger.info(f"Template request - month: {month_param}, year: {year_param}, site: {site_param}, user_role: {current_user.role}")
    
    try:
        # Resolve employees for the requested site through salary code relationships
        if site_param:
            # Join Employee -> WageMaster -> Site to filter by site_id
            from models.wage_master import WageMaster
            from models.site import Site
            employees = Employee.query.join(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).join(
                Site, WageMaster.site_name == Site.site_name
            ).filter(Site.site_id == site_param).order_by(Employee.employee_id.asc()).all()
            logger.info(f"Loading employees for site {site_param} via salary codes: {len(employees)} found")
        else:
            if current_user.role == 'supervisor' and current_user.site_id:
                # For supervisors, filter by their assigned site through salary codes
                from models.wage_master import WageMaster
                from models.site import Site
                employees = Employee.query.join(
                    WageMaster, Employee.salary_code == WageMaster.salary_code
                ).join(
                    Site, WageMaster.site_name == Site.site_name
                ).filter(Site.site_id == current_user.site_id).order_by(Employee.employee_id.asc()).all()
                logger.info(f"Loading employees for supervisor site {current_user.site_id} via salary codes: {len(employees)} found")
            else:
                # For admin users without site filter, load all employees
                employees = Employee.query.order_by(Employee.employee_id.asc()).all()
                logger.info(f"Loading all employees for admin: {len(employees)} found")

        # Get current month and year
        current_date = datetime.now()
        current_month = month_param or current_date.month
        current_year = year_param or current_date.year
        
        # Get the number of days in current month
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        
        # Generate date columns for current month
        date_columns = {}
        for day in range(1, days_in_month + 1):
            date_str = f"{day:02d}/{current_month:02d}/{current_year}"
            # Check if this day is Sunday (weekday() returns 6 for Sunday)
            date_obj = datetime(current_year, current_month, day)
            if date_obj.weekday() == 6:  # Sunday
                date_columns[date_str] = 'OFF'
            else:
                date_columns[date_str] = ''

        # Define all columns in order
        all_columns = ['Employee ID', 'Employee Name'] + list(date_columns.keys()) + ['Overtime']
        
        template_data = []
        logger.info(f"Generating template for {len(employees)} employees, {len(date_columns)} date columns")
        
        for emp in employees:
            # Create base employee data
            employee_row = {
                'Employee ID': getattr(emp, 'employee_id', ''),
                'Employee Name': f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip(),
            }

            # Add all date columns for current month
            employee_row.update(date_columns)
            # Add Overtime column placeholder
            employee_row['Overtime'] = ''
            template_data.append(employee_row)

        # Create DataFrame with explicit columns to preserve headers even when empty
        if template_data:
            df = pd.DataFrame(template_data)
        else:
            # Create empty DataFrame with headers when no employees
            df = pd.DataFrame(columns=all_columns)
            logger.warning("No employees found, creating template with headers only")
        
        logger.info(f"Created DataFrame with shape: {df.shape}")
        logger.info(f"DataFrame columns: {list(df.columns)[:5]}... (showing first 5)")
        
        # Create Excel file in memory
        output = BytesIO()
        
        # Write to Excel
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Attendance')
        
        # Get the workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['Attendance']
        
        # Auto-adjust column widths
        for idx, column in enumerate(df.columns, 1):
            if len(df) > 0:
                column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
            else:
                column_length = len(str(column))
            col_letter = worksheet.cell(1, idx).column_letter
            worksheet.column_dimensions[col_letter].width = min(column_length + 2, 20)
        
        # Save and close the writer
        writer.close()
        
        # Seek to beginning of the stream
        output.seek(0)

        # Include current month/year in filename for clarity
        month_name = calendar.month_name[current_month]
        safe_site = (site_param or 'all').strip().replace(' ', '_') if site_param else 'all'
        filename = f"attendance_template_{safe_site}_{month_name}_{current_year}.xlsx"

        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error generating template: {str(e)}"
        }), 500
        

@attendance_bp.route("/bulk-mark-excel", methods=["POST"])
@token_required
def bulk_mark_attendance_excel(current_user):
    """Optimized bulk mark attendance via Excel file"""
    start_time = time.time()
    
    try:
        # Authorization and file validation (same as original)
        if current_user.role not in ['supervisor', 'admin']:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        file = request.files['file']
        month = request.form.get('month')
        year = request.form.get('year')
        site_id_param = request.form.get('site_id')
        
        if not file or file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
            
        if not month or not year:
            return jsonify({"success": False, "message": "Month and year are required"}), 400
        
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid month or year format"}), 400
        
        # File validation
        allowed_extensions = {'.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({"success": False, "message": "Invalid file type. Please upload an Excel file (.xlsx or .xls)"}), 400
        
        # Read Excel file
        file_data = BytesIO(file.read())
        
        try:
            df = safe_read_excel(file_data)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading Excel file: {str(e)}"}), 400
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip()
        
        # Find required columns (same as original)
        employee_id_col = None
        for col in df.columns:
            if col.lower().replace(' ', '').replace('_', '') in ['employeeid', 'empid', 'id']:
                employee_id_col = col
                break
        
        if not employee_id_col:
            return jsonify({
                "success": False, 
                "message": "Employee ID column not found. Expected column names: 'Employee ID', 'Emp ID', or 'ID'"
            }), 400
        
        # Clean employee IDs
        df[employee_id_col] = (
            df[employee_id_col]
            .astype(str)
            .str.strip()                # remove spaces
            .str.replace('.0', '', regex=False)  # remove Excel float .0
            .str.replace(r'\.0$', '', regex=True) # extra safeguard
        )
        
        # Find employee name column
        employee_name_col = None
        for col in df.columns:
            if col.lower().replace(' ', '').replace('_', '') in ['employeename', 'name', 'empname']:
                employee_name_col = col
                break
        
        if not employee_name_col:
            return jsonify({
                "success": False, 
                "message": "Employee Name column not found. Expected column names: 'Employee Name', 'Name', or 'Emp Name'"
            }), 400
        
        # Find date columns
        date_columns = []
        for col in df.columns:
            if col not in [employee_id_col, employee_name_col, 'Skill Level'] and is_date(col):
                date_columns.append(col)
        
        if not date_columns:
            return jsonify({
                "success": False,
                "message": "No valid date columns found. Expected format: dd/mm/yyyy, dd-mm-yyyy, or datetime objects"
            }), 400
        
        # OPTIMIZATION STARTS HERE
        
        # Step 1: Extract all unique employee IDs from file
        employee_ids_in_file = df[employee_id_col].dropna().astype(str).str.strip().unique()
        employee_ids_in_file = [eid for eid in employee_ids_in_file if eid and eid != 'nan']
        
        # Step 2: Batch load all employees (1 query instead of N queries)
        logger.info(f"Excel IDs (first 10): {employee_ids_in_file[:10]}")

        try:
            effective_site_id = current_user.site_id
            if current_user.role == 'admin' and site_id_param:
                effective_site_id = site_id_param
            employee_dict = batch_load_employees(
                employee_ids_in_file,
                effective_site_id,
                current_user.role
            )
            logger.info(f"DB IDs loaded (first 10): {list(employee_dict.keys())[:10]}")
        except Exception as e:
            logger.error(f"❌ Error loading employees from DB: {e}")
            return jsonify({"error": "Failed to load employees from DB"}), 500

        logger.info(f"Loading {len(employee_ids_in_file)} employees in batch...")
        effective_site_id = current_user.site_id
        if current_user.role == 'admin' and site_id_param:
            effective_site_id = site_id_param
        employee_dict = batch_load_employees(
            employee_ids_in_file, 
            effective_site_id, 
            current_user.role
        )
        
        # Step 3: Parse all dates to determine date range
        all_dates = set()
        for col in date_columns:
            year_from_col, month_from_col, day_from_col = parse_date_from_column(col)
            if year_from_col and month_from_col and day_from_col:
                try:
                    attendance_date = date(year_from_col, month_from_col, day_from_col)
                    all_dates.add(attendance_date)
                except ValueError:
                    continue
        
        if not all_dates:
            return jsonify({
                "success": False,
                "message": "No valid dates found in columns"
            }), 400
        
        min_date = min(all_dates)
        max_date = max(all_dates)
        
        # Step 4: Batch load existing attendance (1 query instead of N queries)
        logger.info(f"Loading existing attendance from {min_date} to {max_date}...")
        existing_attendance_dict = batch_load_existing_attendance(
            list(employee_dict.keys()), 
            min_date, 
            max_date
        )
        
        # Initialize results tracking
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
            "skipped_records": 0,
            "updated_records": 0,
            "new_records": 0
        }
        
        # Step 5: Prepare bulk operations
        new_attendance_records = []
        updated_records = []
        
        logger.info(f"Processing {len(df)} employees with {len(date_columns)} date columns...")
        
        # Process each row
        for index, row in df.iterrows():
            try:
                employee_id = str(row[employee_id_col]).strip()
                
                # Skip empty rows
                if pd.isna(row[employee_id_col]) or employee_id in ['nan', ''] or not employee_id:
                    continue
                
                # Check if employee exists (O(1) lookup instead of database query)
                employee = employee_dict.get(employee_id)
                if not employee:
                    results["errors"].append(f"Employee {employee_id} not found or not in your site")
                    results["failed"] += 1
                    continue
                
                employee_processed = False

                # Optional: read Overtime column (total monthly overtime shifts)
                monthly_overtime_shifts = 0.0
                if 'Overtime' in df.columns:
                    try:
                        raw_ot = row.get('Overtime')
                        if pd.notna(raw_ot) and str(raw_ot).strip() != '':
                            # The overtime column contains total overtime shifts for the entire month
                            monthly_overtime_shifts = float(str(raw_ot).strip())
                            # Round to nearest 0.5 as overtime shifts are typically in 0.5 increments
                            monthly_overtime_shifts = round(monthly_overtime_shifts * 2) / 2.0
                    except Exception:
                        monthly_overtime_shifts = 0.0
                
                # Process each date column for this employee
                first_working_day_processed = False
                for col in date_columns:
                    # Skip blank values
                    if pd.isna(row[col]) or str(row[col]).strip() == '':
                        continue

                    try:
                        attendance_value = normalize_attendance_value(row[col])
                        if not attendance_value:
                            continue

                        # Parse date from column
                        year_from_col, month_from_col, day_from_col = parse_date_from_column(col)
                        if year_from_col and month_from_col and day_from_col:
                            try:
                                attendance_date = date(year_from_col, month_from_col, day_from_col)
                            except ValueError:
                                continue

                            # Calculate overtime for this day
                            day_overtime = 0.0
                            if monthly_overtime_shifts > 0 and attendance_value not in ['Absent', 'Leave', 'Holiday']:
                                if not first_working_day_processed:
                                    # Apply total monthly overtime to first working day
                                    day_overtime = monthly_overtime_shifts
                                    first_working_day_processed = True
                                else:
                                    day_overtime = 0.0  # Overtime already applied to first working day

                            # Check if attendance exists (O(1) lookup instead of database query)
                            existing_key = f"{employee.employee_id}_{attendance_date}"
                            existing = existing_attendance_dict.get(existing_key)

                            if existing:
                                # Mark for update
                                existing.attendance_status = attendance_value
                                # Update overtime if provided
                                if day_overtime > 0:
                                    existing.overtime_shifts = day_overtime
                                existing.marked_by = current_user.role
                                existing.updated_by = current_user.email
                                existing.updated_date = datetime.utcnow()
                                updated_records.append(existing)
                                results["updated_records"] += 1
                            else:
                                # Prepare for bulk insert
                                new_record = {
                                    'attendance_id': str(uuid.uuid4()),
                                    'employee_id': employee.employee_id,
                                    'attendance_date': attendance_date,
                                    'attendance_status': attendance_value,
                                    'overtime_shifts': day_overtime,
                                    'marked_by': current_user.role,
                                    'created_by': current_user.email,
                                    'created_date': datetime.utcnow(),
                                    'total_hours_worked': 8.0,
                                    'is_approved': True,
                                    'is_weekend': attendance_date.weekday() >= 5,
                                    'is_holiday': False  # You can enhance this with holiday check
                                }
                                new_attendance_records.append(new_record)
                                results["new_records"] += 1

                            employee_processed = True

                    except Exception as e:
                        logger.error(f"Error processing column {col} for employee {employee_id}: {str(e)}")
                        results["errors"].append(f"Error processing column {col} for employee {employee_id}: {str(e)}")
                
                if employee_processed:
                    results["successful"] += 1
                else:
                    results["skipped_records"] += 1
                    
                results["processed"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error processing employee {row.get(employee_id_col, 'Unknown')}: {str(e)}")
                results["failed"] += 1
                results["processed"] += 1
        
        # Step 6: Execute bulk operations
        try:
            # Bulk insert new records
            if new_attendance_records:
                logger.info(f"Bulk inserting {len(new_attendance_records)} new records...")
                bulk_results = safe_bulk_insert(new_attendance_records, chunk_size=1000)
                results["errors"].extend(bulk_results["errors"])
            
            # Commit all changes (updates + new records)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk operation failed: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Bulk operation failed: {str(e)}"
            }), 500
        
        # Calculate performance metrics
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        return jsonify({
            "success": True,
            "message": f"Optimized bulk attendance upload completed in {processing_time}s",
            "performance": {
                "processing_time_seconds": processing_time,
                "employees_loaded": len(employee_dict),
                "existing_records_loaded": len(existing_attendance_dict),
                "date_columns_processed": len(date_columns)
            },
            "results": {
                "total_records": results["new_records"] + results["updated_records"],
                "new_records": results["new_records"],
                "updated_records": results["updated_records"],
                "skipped_records": results["skipped_records"],
                "successful_employees": results["successful"],
                "failed_employees": results["failed"],
                "errors": results["errors"][:10]  # Limit error list for response size
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in optimized bulk-mark-excel: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        return jsonify({
            "success": False,
            "message": f"Error processing file: {str(e)}"
        }), 500

@attendance_bp.route("/debug-columns", methods=["POST"])
@token_required
def debug_columns(current_user):
    """Debug endpoint to check column detection"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
        
        # Read Excel file
        file_data = BytesIO(file.read())
        df = safe_read_excel(file_data, dtype=str)
        
        # Clean up column names
        df.columns = df.columns.str.strip()
        
        # Debug info
        debug_info = {
            "total_columns": len(df.columns),
            "all_columns": list(df.columns),
            "date_columns": [],
            "non_date_columns": [],
            "column_analysis": {}
        }
        
        for col in df.columns:
            is_date_col = is_date(col)
            debug_info["column_analysis"][col] = {
                "is_date": is_date_col,
                "column_str": str(col).strip(),
                "column_type": type(col).__name__
            }
            
            if is_date_col:
                debug_info["date_columns"].append(col)
                # Try to parse it
                year, month, day = parse_date_from_column(col)
                debug_info["column_analysis"][col]["parsed_date"] = {
                    "year": year,
                    "month": month,
                    "day": day
                }
            else:
                debug_info["non_date_columns"].append(col)
        
        return jsonify({
            "success": True,
            "debug_info": debug_info
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Debug error: {str(e)}"
        }), 500