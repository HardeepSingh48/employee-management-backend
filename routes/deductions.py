from flask import Blueprint, request, jsonify
from models import db
from models.deduction import Deduction
from models.employee import Employee
from datetime import datetime
import pandas as pd
import io
import uuid
from routes.auth import token_required

deductions_bp = Blueprint("deductions", __name__)

@deductions_bp.route("/", methods=["GET"])
@token_required
def get_deductions(current_user):
    """Get all deductions with employee details"""
    try:
        site_id = request.args.get('site_id')

        query = db.session.query(Deduction, Employee).join(
            Employee, Deduction.employee_id == Employee.employee_id
        )

        # Apply site filtering if site_id is provided
        if site_id:
            from models.site import Site
            from models.wage_master import WageMaster

            site = Site.query.filter_by(site_id=site_id).first()
            if site:
                # Get salary codes for the selected site
                site_salary_codes = WageMaster.query.filter_by(site_name=site.site_name).with_entities(WageMaster.salary_code).all()
                site_salary_codes = [code[0] for code in site_salary_codes]

                if site_salary_codes:
                    query = query.filter(Employee.salary_code.in_(site_salary_codes))
                else:
                    # No salary codes for this site, return empty result
                    query = query.filter(Deduction.employee_id == None)  # This will return no results

        deductions = query.all()
        
        result = []
        for deduction, employee in deductions:
            result.append({
                'deduction_id': deduction.deduction_id,
                'employee_id': deduction.employee_id,
                'employee_name': f"{employee.first_name} {employee.last_name}",
                'deduction_type': deduction.deduction_type,
                'total_amount': float(deduction.total_amount),
                'months': deduction.months,
                'monthly_installment': deduction.monthly_installment(),
                'start_month': deduction.start_month.strftime('%Y-%m-%d'),
                'created_at': deduction.created_at.strftime('%Y-%m-%d %H:%M:%S') if deduction.created_at else None,
                'status': 'Active' if deduction.is_active_for_month(datetime.now().year, datetime.now().month) else 'Completed'
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching deductions: {str(e)}'
        }), 500

@deductions_bp.route("/", methods=["POST"])
@token_required
def create_deduction(current_user):
    """Create a new deduction"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['employee_id', 'deduction_type', 'total_amount', 'months', 'start_month']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Check if employee exists
        employee = Employee.query.filter_by(employee_id=data['employee_id']).first()
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Employee not found'
            }), 404
        
        # Parse start_month date
        try:
            start_month = datetime.strptime(data['start_month'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid start_month format. Use YYYY-MM-DD'
            }), 400

        # Validate start_month is not in the past (current month or later)
        current_date = datetime.now().date()
        current_month_start = current_date.replace(day=1)  # First day of current month

        if start_month < current_month_start:
            return jsonify({
                'success': False,
                'message': 'Start month cannot be in the past. Please select current month or a future month.'
            }), 400
        
        # Create deduction
        deduction = Deduction(
            deduction_id=str(uuid.uuid4()),
            employee_id=data['employee_id'],
            deduction_type=data['deduction_type'],
            total_amount=data['total_amount'],
            months=data['months'],
            start_month=start_month,
            created_by=data.get('created_by', 'system')
        )
        
        db.session.add(deduction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Deduction created successfully',
            'data': {
                'deduction_id': deduction.deduction_id,
                'employee_id': deduction.employee_id,
                'deduction_type': deduction.deduction_type,
                'total_amount': float(deduction.total_amount),
                'months': deduction.months,
                'monthly_installment': deduction.monthly_installment(),
                'start_month': deduction.start_month.strftime('%Y-%m-%d')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error creating deduction: {str(e)}'
        }), 500

@deductions_bp.route("/<deduction_id>", methods=["PUT"])
@token_required
def update_deduction(current_user, deduction_id):
    """Update an existing deduction"""
    try:
        deduction = Deduction.query.filter_by(deduction_id=deduction_id).first()
        if not deduction:
            return jsonify({
                'success': False,
                'message': 'Deduction not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Update fields if provided
        if 'deduction_type' in data:
            deduction.deduction_type = data['deduction_type']
        if 'total_amount' in data:
            deduction.total_amount = data['total_amount']
        if 'months' in data:
            deduction.months = data['months']
        if 'start_month' in data:
            try:
                start_month = datetime.strptime(data['start_month'], '%Y-%m-%d').date()

                # Validate start_month is not in the past (current month or later)
                current_date = datetime.now().date()
                current_month_start = current_date.replace(day=1)  # First day of current month

                if start_month < current_month_start:
                    return jsonify({
                        'success': False,
                        'message': 'Start month cannot be in the past. Please select current month or a future month.'
                    }), 400

                deduction.start_month = start_month
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid start_month format. Use YYYY-MM-DD'
                }), 400
        
        deduction.updated_by = data.get('updated_by', 'system')
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Deduction updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating deduction: {str(e)}'
        }), 500

@deductions_bp.route("/<deduction_id>", methods=["DELETE"])
@token_required
def delete_deduction(current_user, deduction_id):
    """Delete a deduction"""
    try:
        deduction = Deduction.query.filter_by(deduction_id=deduction_id).first()
        if not deduction:
            return jsonify({
                'success': False,
                'message': 'Deduction not found'
            }), 404
        
        db.session.delete(deduction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Deduction deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting deduction: {str(e)}'
        }), 500

@deductions_bp.route("/bulk", methods=["POST"])
@token_required
def bulk_upload_deductions(current_user):
    """Bulk upload deductions from Excel/CSV file"""
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({
                'success': False,
                'message': 'No file provided'
            }), 400
        
        # Read the file
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            return jsonify({
                'success': False,
                'message': 'Unsupported file format. Please upload Excel (.xlsx) or CSV file'
            }), 400
        
        # Validate required columns
        required_columns = ['Employee ID', 'Deduction Type', 'Total Amount', 'Months', 'Start Month']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                'success': False,
                'message': f'Missing required columns: {", ".join(missing_columns)}'
            }), 400
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Validate employee exists
                employee_id = str(row['Employee ID']).strip()
                employee = Employee.query.filter_by(employee_id=employee_id).first()
                if not employee:
                    errors.append(f"Row {index + 1}: Employee {employee_id} not found")
                    error_count += 1
                    continue
                
                # Parse start month
                try:
                    if pd.isna(row['Start Month']):
                        start_month = datetime.now().date()
                    else:
                        start_month = pd.to_datetime(row['Start Month']).date()
                except:
                    start_month = datetime.now().date()
                
                # Create deduction
                deduction = Deduction(
                    deduction_id=str(uuid.uuid4()),
                    employee_id=employee_id,
                    deduction_type=str(row['Deduction Type']).strip(),
                    total_amount=float(row['Total Amount']),
                    months=int(row['Months']),
                    start_month=start_month,
                    created_by='bulk_upload'
                )
                
                db.session.add(deduction)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
                error_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Bulk upload completed. {success_count} deductions created, {error_count} errors',
            'data': {
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing bulk upload: {str(e)}'
        }), 500

@deductions_bp.route("/template", methods=["GET"])
@token_required
def download_template(current_user):
    """Download Excel template for bulk upload"""
    try:
        # Create sample data
        sample_data = {
            'Employee ID': ['91510001', '91510002'],
            'Deduction Type': ['Clothes', 'Loan'],
            'Total Amount': [20000, 15000],
            'Months': [9, 6],
            'Start Month': ['2025-08-01', '2025-09-01']
        }
        
        df = pd.DataFrame(sample_data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Deductions', index=False)
        
        output.seek(0)
        
        return output.getvalue(), 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=deductions_template.xlsx'
        }
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error generating template: {str(e)}'
        }), 500

@deductions_bp.route("/employee/<employee_id>", methods=["GET"])
@token_required
def get_employee_deductions(current_user, employee_id):
    """Get all deductions for a specific employee"""
    try:
        deductions = Deduction.query.filter_by(employee_id=employee_id).all()
        
        result = []
        for deduction in deductions:
            result.append({
                'deduction_id': deduction.deduction_id,
                'deduction_type': deduction.deduction_type,
                'total_amount': float(deduction.total_amount),
                'months': deduction.months,
                'monthly_installment': deduction.monthly_installment(),
                'start_month': deduction.start_month.strftime('%Y-%m-%d'),
                'created_at': deduction.created_at.strftime('%Y-%m-%d %H:%M:%S') if deduction.created_at else None,
                'status': 'Active' if deduction.is_active_for_month(datetime.now().year, datetime.now().month) else 'Completed'
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching employee deductions: {str(e)}'
        }), 500







