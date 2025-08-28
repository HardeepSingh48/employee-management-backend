from flask import Blueprint, request, jsonify,send_file
from services.attendance_service import AttendanceService
from models import db
from models.employee import Employee
from models.attendance import Attendance
from datetime import datetime, date
import json
import pandas as pd
from io import BytesIO
from routes.auth import token_required
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

attendance_bp = Blueprint("attendance", __name__)

STATUS_MAP = {
    'P': 'Present',
    'A': 'Absent',
    'L': 'Late',
    'HD': 'Half Day',
    'H': 'Holiday',
    'LV': 'Leave',
    'Present': 'Present',
    'Absent': 'Absent',
    'Late': 'Late',
    'Half Day': 'Half Day',
    'Holiday': 'Holiday',
    'Leave': 'Leave'
}

def round_to_half(x):
    """Round to nearest 0.5 increment"""
    return round(x * 2) / 2.0

def normalize_attendance_value(value):
    """Normalize attendance value and return the mapped status"""
    if not value or pd.isna(value):
        return None
    
    # Convert to string and clean up
    v = str(value).strip().upper()
    
    # Handle common variations
    if v in ['P', 'PRESENT']:
        return 'Present'
    elif v in ['A', 'ABSENT']:
        return 'Absent'
    elif v in ['L', 'LATE']:
        return 'Late'
    elif v in ['HD', 'H', 'HALF DAY', 'HALFDAY']:
        return 'Half Day'
    elif v in ['HOL', 'HOLIDAY']:
        return 'Holiday'
    elif v in ['LV', 'LEAVE']:
        return 'Leave'
    else:
        # Try original mapping as fallback
        return STATUS_MAP.get(v.title())

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


def is_date(col):
    """Check if column name represents a date"""
    from datetime import datetime
    import re
    import pandas as pd
    import math

    # Handle None or NaN values
    if col is None or (isinstance(col, float) and math.isnan(col)):
        return False

    # If it's already a datetime object or pandas Timestamp, accept it
    if isinstance(col, (datetime, pd.Timestamp)):
        return True

    # Convert to string and clean up
    try:
        col_str = str(col).strip()
    except:
        return False

    # Skip empty strings or common non-date columns
    if not col_str or col_str.lower() in ['employee id', 'employee name', 'skill level', 'emp id', 'name', 'nan', '']:
        return False

    # Check if it's a datetime string format (from pandas parsing)
    # Pattern for "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
    datetime_patterns = [
        r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$',  # 2025-08-01 00:00:00
        r'^\d{4}-\d{2}-\d{2}$',                      # 2025-08-01
    ]
    
    for pattern in datetime_patterns:
        if re.match(pattern, col_str):
            try:
                # Try to parse as datetime
                if ' ' in col_str:
                    datetime.strptime(col_str, '%Y-%m-%d %H:%M:%S')
                else:
                    datetime.strptime(col_str, '%Y-%m-%d')
                return True
            except ValueError:
                continue

    # Pattern for dd/mm/yyyy, dd-mm-yyyy formats (original logic)
    date_patterns = [
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$',  # dd/mm/yyyy or dd-mm-yyyy
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$',   # dd/mm/yy or dd-mm-yy
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                day_str, month_str, year_str = match.groups()
                day = int(day_str)
                month = int(month_str)
                year = int(year_str)
                
                # Handle 2-digit years
                if year < 100:
                    year = 2000 + year if year < 30 else 1900 + year
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return True
            except (ValueError, TypeError, OverflowError):
                continue
    
    return False


def parse_date_from_column(col):
    """Parse date from column name"""
    from datetime import datetime
    import re
    import pandas as pd
    import math

    # Handle None or NaN values
    if col is None or (isinstance(col, float) and math.isnan(col)):
        return None, None, None

    # If it's already a datetime object or pandas Timestamp, extract components
    if isinstance(col, (datetime, pd.Timestamp)):
        return col.year, col.month, col.day

    try:
        col_str = str(col).strip()
    except:
        return None, None, None
    
    # Check if it's a datetime string format (from pandas parsing)
    datetime_patterns = [
        r'^(\d{4})-(\d{2})-(\d{2})\s\d{2}:\d{2}:\d{2}$',  # 2025-08-01 00:00:00
        r'^(\d{4})-(\d{2})-(\d{2})$',                      # 2025-08-01
    ]
    
    for pattern in datetime_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                year_str, month_str, day_str = match.groups()
                year = int(year_str)
                month = int(month_str)
                day = int(day_str)
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return year, month, day
            except (ValueError, TypeError, OverflowError):
                continue
    
    # Pattern for dd/mm/yyyy, dd-mm-yyyy formats (original logic)
    date_patterns = [
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$',  # dd/mm/yyyy or dd-mm-yyyy
        r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$',   # dd/mm/yy or dd-mm-yy
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, col_str)
        if match:
            try:
                day_str, month_str, year_str = match.groups()
                day = int(day_str)
                month = int(month_str)
                year = int(year_str)
                
                # Handle 2-digit years
                if year < 100:
                    year = 2000 + year if year < 30 else 1900 + year
                
                # Validate date ranges
                if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                    continue
                
                # Try to create the date to validate it
                datetime(year, month, day)
                return year, month, day
            except (ValueError, TypeError, OverflowError):
                continue
    
    return None, None, None


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

        # For supervisors, verify employee belongs to their site
        if current_user.role == 'supervisor':
            from models.employee import Employee
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            if not employee or employee.site_id != current_user.site_id:
                return jsonify({"success": False, "message": "Employee not found or not in your site"}), 403

        # Optional fields with defaults
        attendance_date = data.get('attendance_date', date.today().isoformat())
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

        # For supervisors, verify all employees belong to their site
        if current_user.role == 'supervisor':
            for record in attendance_records:
                employee = Employee.query.filter_by(employee_id=record.get('employee_id')).first()
                if not employee or employee.site_id != current_user.site_id:
                    return jsonify({
                        "success": False,
                        "message": f"Employee {record.get('employee_id')} not found or not in your site"
                    }), 403

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
    Get all employees for supervisor's site
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        if current_user.role == 'supervisor':
            employees = Employee.query.filter_by(site_id=current_user.site_id).all()
        else:
            employees = Employee.query.all()
        
        employee_data = []
        for emp in employees:
            employee_data.append({
                'employee_id': emp.employee_id,
                'first_name': emp.first_name,
                'last_name': emp.last_name,
                'full_name': f"{emp.first_name} {emp.last_name}",
                'site_id': emp.site_id,
                'department_name': emp.department.department_name if emp.department else None,
                'designation': emp.designation
            })
        
        return jsonify({
            "success": True,
            "data": employee_data,
            "count": len(employee_data)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error fetching site employees: {str(e)}"
        }), 500

@attendance_bp.route("/site-attendance", methods=["GET"])
@token_required
def get_site_attendance(current_user):
    """
    Get attendance records for supervisor's site with filtering
    """
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        
        # Build query
        query = Attendance.query.join(Employee)
        
        if current_user.role == 'supervisor':
            query = query.filter(Employee.site_id == current_user.site_id)
        
        if start_date:
            query = query.filter(Attendance.attendance_date >= start_date)
        
        if end_date:
            query = query.filter(Attendance.attendance_date <= end_date)
        
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)
        
        # Get results
        attendance_records = query.order_by(Attendance.attendance_date.desc()).all()
        
        # Format results
        results = []
        for record in attendance_records:
            results.append({
                'attendance_id': record.attendance_id,
                'employee_id': record.employee_id,
                'employee_name': f"{record.employee.first_name} {record.employee.last_name}",
                'attendance_date': record.attendance_date.isoformat(),
                'attendance_status': record.attendance_status,
                'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                'overtime_shifts': record.overtime_shifts,
                'overtime_hours': record.overtime_hours,
                'total_hours_worked': record.total_hours_worked,
                'remarks': record.remarks,
                'marked_by': record.marked_by,
                'created_date': record.created_date.isoformat() if record.created_date else None
            })
        
        return jsonify({
            "success": True,
            "data": results,
            "count": len(results)
        }), 200
        
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
                
                # For supervisors, check if employee belongs to their site
                if current_user.role == 'supervisor' and employee.site_id != current_user.site_id:
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
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        if current_user.role == 'supervisor':
            employees = Employee.query.filter_by(site_id=current_user.site_id).all()
        else:
            employees = Employee.query.all()

        template_data = []
        for emp in employees:
            template_data.append({
                'Employee ID': emp.employee_id,
                'Employee Name': f"{emp.first_name} {emp.last_name}",
                'Skill Level': '',  # Add this column as it's expected in your file
                '01/08/2025': '',
                '02/08/2025': '',
                '03/08/2025': '',
                '04/08/2025': '',
                '05/08/2025': '',
                # Add more dates for the full month if needed
                '06/08/2025': '',
                '07/08/2025': '',
                '08/08/2025': '',
                '09/08/2025': '',
                '10/08/2025': '',
                '11/08/2025': '',
                '12/08/2025': '',
                '13/08/2025': '',
                '14/08/2025': '',
                '15/08/2025': '',
                '16/08/2025': '',
                '17/08/2025': '',
                '18/08/2025': '',
                '19/08/2025': '',
                '20/08/2025': '',
                '21/08/2025': '',
                '22/08/2025': '',
                '23/08/2025': '',
                '24/08/2025': '',
                '25/08/2025': '',
                '26/08/2025': '',
                '27/08/2025': '',
                '28/08/2025': '',
                '29/08/2025': '',
                '30/08/2025': '',
                '31/08/2025': '',
            })
        
        df = pd.DataFrame(template_data)
        output = BytesIO()
        
        # Use xlsxwriter engine for better compatibility
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Attendance')
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Attendance']
            
            # Auto-adjust column widths
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                worksheet.column_dimensions[worksheet.cell(1, col_idx + 1).column_letter].width = min(column_length + 2, 20)
        
        output.seek(0)

        return send_file(
            output,
            download_name="attendance_template.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error generating template: {str(e)}"
        }), 500

@attendance_bp.route("/bulk-mark-excel", methods=["POST"])
@token_required
def bulk_mark_attendance_excel(current_user):
    """Bulk mark attendance via Excel file (supervisor only)"""
    try:
        # Check authorization
        if current_user.role not in ['supervisor', 'admin']:
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
        
        file = request.files['file']
        month = request.form.get('month')
        year = request.form.get('year')
        
        if not file or file.filename == '':
            return jsonify({"success": False, "message": "No file selected"}), 400
            
        if not month or not year:
            return jsonify({"success": False, "message": "Month and year are required"}), 400
        
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid month or year format"}), 400
        
        # Validate file type
        allowed_extensions = {'.xlsx', '.xls'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({"success": False, "message": "Invalid file type. Please upload an Excel file (.xlsx or .xls)"}), 400
        
        # Create a BytesIO object from the uploaded file
        file_data = BytesIO(file.read())
        
        # Read Excel file using safe method - DON'T force dtype=str for all columns
        try:
            df = safe_read_excel(file_data)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading Excel file: {str(e)}"}), 400
        
        # Convert column names to string to handle datetime objects
        df.columns = df.columns.astype(str).str.strip()
        
        # Fix Employee ID column - convert to string and remove .0 if present
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
        
        # Convert Employee ID to string and clean up
        df[employee_id_col] = df[employee_id_col].astype(str).str.replace('.0', '', regex=False)
        
        # Look for employee name column
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
        
        # Process attendance data
        results = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": [],
            "skipped_records": 0,
            "updated_records": 0,
            "new_records": 0
        }
        
        # Find date columns - now handles both datetime objects and string formats
        date_columns = []
        for col in df.columns:
            if col not in [employee_id_col, employee_name_col, 'Skill Level'] and is_date(col):
                date_columns.append(col)
        
        if not date_columns:
            return jsonify({
                "success": False,
                "message": "No valid date columns found. Expected format: dd/mm/yyyy, dd-mm-yyyy, or datetime objects"
            }), 400
        
        logger.info(f"Found {len(date_columns)} date columns: {date_columns[:5]}...")  # Show first 5 for debugging
        
        # Process each row
        for index, row in df.iterrows():
            try:
                employee_id = str(row[employee_id_col]).strip()
                
                # Skip empty rows
                if pd.isna(row[employee_id_col]) or employee_id in ['nan', ''] or not employee_id:
                    continue
                
                # Check if employee exists and belongs to supervisor's site
                employee = Employee.query.filter_by(employee_id=employee_id).first()
                if not employee:
                    results["errors"].append(f"Employee {employee_id} not found")
                    results["failed"] += 1
                    continue
                
                # For supervisors, check if employee belongs to their site
                if current_user.role == 'supervisor' and employee.site_id != current_user.site_id:
                    results["errors"].append(f"Employee {employee_id} not in your site")
                    results["failed"] += 1
                    continue
                
                employee_processed = False
                
                # Process attendance for each date column
                for col in date_columns:
                    # Skip blank or invalid values
                    if pd.isna(row[col]) or str(row[col]).strip() == '':
                        continue
                    
                    try:
                        attendance_value = normalize_attendance_value(row[col])

                        if not attendance_value:
                            logger.warning(f"Skipping invalid attendance value '{row[col]}' in column {col} for employee {employee_id}")
                            continue
                        
                        # Parse date from column name using updated helper function
                        year_from_col, month_from_col, day_from_col = parse_date_from_column(col)
                        
                        if year_from_col and month_from_col and day_from_col:
                            attendance_date = date(year_from_col, month_from_col, day_from_col)
                            
                            # Check if attendance already exists
                            existing = Attendance.query.filter_by(
                                employee_id=employee.employee_id,
                                attendance_date=attendance_date
                            ).first()
                            
                            if existing:
                                # Update existing record
                                existing.attendance_status = attendance_value
                                existing.marked_by = current_user.role
                                existing.updated_by = current_user.email
                                existing.updated_date = datetime.utcnow()
                                results["updated_records"] += 1
                                logger.info(f"Updated attendance for {employee_id} on {attendance_date}: {attendance_value}")
                            else:
                                # Create new record
                                attendance = Attendance(
                                    employee_id=employee.employee_id,
                                    attendance_date=attendance_date,
                                    attendance_status=attendance_value,
                                    marked_by=current_user.role,
                                    created_by=current_user.email,
                                    created_date=datetime.utcnow()
                                )
                                db.session.add(attendance)
                                results["new_records"] += 1
                                logger.info(f"Added new attendance for {employee_id} on {attendance_date}: {attendance_value}")
                            
                            employee_processed = True
                            
                        else:
                            results["errors"].append(f"Could not parse date from column {col} for employee {employee_id}")
                            
                    except Exception as e:
                        # Log error but continue processing other columns
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
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Bulk attendance upload completed. Processed {results['processed']} employees, {results['successful']} successful, {results['failed']} failed. Found {len(date_columns)} date columns.",
            "total_records": results["new_records"] + results["updated_records"],
            "new_records": results["new_records"],
            "updated_records": results["updated_records"],
            "skipped_records": results["skipped_records"],
            "results": results,
            "date_columns_processed": len(date_columns)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in bulk-mark-excel: {str(e)}")
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