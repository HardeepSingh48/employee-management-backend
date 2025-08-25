from flask import Blueprint, request, jsonify
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
    """
    Check if a column name represents a valid date in dd/mm/yyyy format
    """
    import re
    from datetime import datetime
    
    # Pattern for dd/mm/yyyy or dd-mm-yyyy format
    date_pattern = r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$'
    
    match = re.match(date_pattern, str(col).strip())
    if not match:
        return False
    
    try:
        day, month, year = match.groups()
        # Validate the date
        datetime(int(year), int(month), int(day))
        return True
    except ValueError:
        return False

def parse_date_from_column(col):
    """
    Parse date from column name in dd/mm/yyyy format
    Returns (year, month, day) tuple
    """
    import re
    
    date_pattern = r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$'
    match = re.match(date_pattern, str(col).strip())
    
    if match:
        day, month, year = match.groups()
        return int(year), int(month), int(day)
    
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
    """Download attendance template for supervisors"""
    if current_user.role not in ['supervisor', 'admin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        # Get employees for the supervisor's site
        if current_user.role == 'supervisor':
            employees = Employee.query.filter_by(site_id=current_user.site_id).all()
        else:
            employees = Employee.query.all()
        
        # Create template data
        template_data = []
        for emp in employees:
            template_data.append({
                'Employee ID': emp.employee_id,
                'Employee Name': f"{emp.first_name} {emp.last_name}",
                'Site': emp.site_id or '',
                'Monday 1': '',
                'Tuesday 2': '',
                'Wednesday 3': '',
                'Thursday 4': '',
                'Friday 5': '',
                'Saturday 6': '',
                'Sunday 7': '',
                # Add more days as needed
            })
        
        return jsonify({
            "success": True,
            "message": "Template data generated",
            "data": template_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
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
        
        # Read Excel file using safe method
        try:
            df = safe_read_excel(file_data)
        except Exception as e:
            return jsonify({"success": False, "message": f"Error reading Excel file: {str(e)}"}), 400
        
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
        
        # Find date columns (only columns with valid date format)
        date_columns = [col for col in df.columns if is_date(col)]
        
        if not date_columns:
            return jsonify({
                "success": False,
                "message": "No valid date columns found. Expected format: dd/mm/yyyy or dd-mm-yyyy"
            }), 400
        
        logger.info(f"Found {len(date_columns)} date columns: {date_columns}")
        
        for _, row in df.iterrows():
            try:
                employee_id = str(row['Employee ID']).strip()
                
                # Skip empty rows
                if pd.isna(row['Employee ID']) or employee_id == 'nan' or not employee_id:
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
                
                # Process attendance for each date column
                for col in date_columns:
                    # Skip blank or invalid values
                    if pd.isna(row[col]) or str(row[col]).strip() == '':
                        continue
                    
                    try:
                        attendance_value = str(row[col]).strip().upper()
                        
                        # Validate attendance value
                        if attendance_value in ['P', 'A', 'L', 'H']:
                            # Parse date from column name using helper function
                            year_from_col, month_from_col, day_from_col = parse_date_from_column(col)
                            
                            if year_from_col and month_from_col and day_from_col:
                                attendance_date = f"{year_from_col}-{month_from_col:02d}-{day_from_col:02d}"
                                
                                # Check if attendance already exists
                                existing = Attendance.query.filter_by(
                                    employee_id=employee.employee_id,
                                    attendance_date=attendance_date
                                ).first()
                                
                                if not existing:
                                    attendance = Attendance(
                                        employee_id=employee.employee_id,
                                        attendance_date=attendance_date,
                                        attendance_status=attendance_value,
                                        marked_by=current_user.role,
                                        created_by=current_user.email
                                    )
                                    db.session.add(attendance)
                                    logger.info(f"Added attendance for {employee_id} on {attendance_date}: {attendance_value}")
                                else:
                                    logger.info(f"Attendance already exists for {employee_id} on {attendance_date}, skipping")
                            else:
                                results["errors"].append(f"Could not parse date from column {col} for employee {employee_id}")
                        else:
                            # Skip invalid attendance values without throwing errors
                            logger.warning(f"Skipping invalid attendance value '{attendance_value}' in column {col} for employee {employee_id}")
                            
                    except Exception as e:
                        # Log error but continue processing other columns
                        logger.error(f"Error processing column {col} for employee {employee_id}: {str(e)}")
                        results["errors"].append(f"Error processing column {col} for employee {employee_id}: {str(e)}")
                
                results["successful"] += 1
                results["processed"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error processing employee {row.get('Employee ID', 'Unknown')}: {str(e)}")
                results["failed"] += 1
                results["processed"] += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Bulk attendance upload completed. Processed {results['processed']} employees, {results['successful']} successful, {results['failed']} failed. Found {len(date_columns)} date columns.",
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