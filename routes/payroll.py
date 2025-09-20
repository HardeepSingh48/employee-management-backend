from flask import Blueprint, request, jsonify, make_response, send_file
from models import db
from models.employee import Employee
from models.user import User
from services.salary_service import SalaryService
from services.attendance_service import AttendanceService
from routes.auth import token_required
from datetime import datetime, date
import json
import os
import tempfile
import uuid
from functools import wraps
from services.pdf_service import generate_payroll_pdf

# Import PDF generation libraries
try:
    import pdfkit
    PDF_GENERATOR = 'wkhtmltopdf'
except ImportError:
    try:
        from weasyprint import HTML, CSS
        PDF_GENERATOR = 'weasyprint'
    except ImportError:
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            PDF_GENERATOR = 'reportlab'
        except ImportError:
            PDF_GENERATOR = None

payroll_bp = Blueprint('payroll', __name__)

def require_admin_or_supervisor(f):
    """Decorator to ensure only Admin or Supervisor can access payroll endpoints"""
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        try:
            allowed_roles = ['admin', 'supervisor', 'hr', 'manager']  # Include hr and manager as they have admin-level access
            if not current_user or current_user.role not in allowed_roles:
                return jsonify({'success': False, 'message': f'Access denied. Admin or Supervisor role required. Current role: {current_user.role if current_user else "None"}'}), 403
                
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'success': False, 'message': 'Authentication error', 'error': str(e)}), 401
    
    return decorated_function

def number_to_words(num):
    """Convert number to words (Indian format)"""
    if num == 0:
        return "Zero"
    
    def convert_hundreds(n):
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
                "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        result = ""
        
        if n >= 100:
            result += ones[n // 100] + " Hundred "
            n %= 100
            
        if n >= 20:
            result += tens[n // 10]
            if n % 10 != 0:
                result += " " + ones[n % 10]
        elif n > 0:
            result += ones[n]
            
        return result.strip()
    
    if num < 0:
        return "Minus " + number_to_words(-num)
    
    # Handle Indian number system (lakhs, crores)
    crores = num // 10000000
    lakhs = (num % 10000000) // 100000
    thousands = (num % 100000) // 1000
    hundreds = num % 1000
    
    result = ""
    
    if crores > 0:
        result += convert_hundreds(crores) + " Crore "
    if lakhs > 0:
        result += convert_hundreds(lakhs) + " Lakh "
    if thousands > 0:
        result += convert_hundreds(thousands) + " Thousand "
    if hundreds > 0:
        result += convert_hundreds(hundreds)
    
    return result.strip()

def generate_payslip_html(employee_data, year, month):
    """Generate optimized HTML for a single payslip (compact layout)"""
    
    try:
        # Calculate salary using existing service
        salary_result = SalaryService.calculate_individual_salary(
            employee_data['Employee ID'], year, month
        )
        
        if not salary_result['success']:
            return f"<div>Error calculating salary for {employee_data['Employee Name']}: {salary_result.get('message', 'Unknown error')}</div>"
    except Exception as e:
        return f"<div>Exception calculating salary for {employee_data['Employee Name']}: {str(e)}</div>"
    
    salary_data = salary_result['data']
    
    # Get employee details
    employee = Employee.query.filter_by(employee_id=employee_data['Employee ID']).first()
    
    # Format amounts with better handling
    def format_amount(amount):
        try:
            return f"{float(amount):,.2f}" if amount else "0.00"
        except (ValueError, TypeError):
            return "0.00"
    
    # Get month name
    month_names = ['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    month_name = month_names[month] if 1 <= month <= 12 else 'UNK'
    
    # Build earnings list with better organization
    earnings = []
    
    # Primary earnings
    if float(salary_data.get('Basic', 0)) > 0:
        earnings.append(('Basic', salary_data.get('Basic', 0)))
    
    if float(salary_data.get('Special Basic', 0)) > 0:
        earnings.append(('Spl Basic', salary_data.get('Special Basic', 0)))
    
    if float(salary_data.get('DA', 0)) > 0:
        earnings.append(('DA', salary_data.get('DA', 0)))
    
    if float(salary_data.get('HRA', 0)) > 0:
        earnings.append(('HRA', salary_data.get('HRA', 0)))
    
    if float(salary_data.get('Overtime', 0)) > 0:
        earnings.append(('Overtime', salary_data.get('Overtime', 0)))
    
    if float(salary_data.get('Overtime Allowance', 0)) > 0:
        earnings.append(('OT Allow', salary_data.get('Overtime Allowance', 0)))
    
    if float(salary_data.get('Others', 0)) > 0:
        earnings.append(('Others', salary_data.get('Others', 0)))
    
    # Build deductions list with better organization
    deductions = []
    
    # Standard deductions
    standard_deductions = [
        ('PF', salary_data.get('PF', 0)),
        ('ESIC', salary_data.get('ESIC', 0)),
        ('Society', salary_data.get('Society', 0)),
        ('Inc Tax', salary_data.get('Income Tax', 0)),
        ('Insurance', salary_data.get('Insurance', 0)),
        ('Other Rec', salary_data.get('Others Recoveries', 0)),
    ]
    
    for name, amount in standard_deductions:
        if float(amount) > 0:
            deductions.append((name, amount))
    
    # Add dynamic deductions from the deductions module (with shorter names)
    for key, value in salary_data.items():
        if key not in ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 
                       'Basic', 'Special Basic', 'DA', 'HRA', 'Overtime', 'Overtime Allowance', 'Others', 'Total Earnings',
                       'PF', 'ESIC', 'Society', 'Income Tax', 'Insurance', 'Others Recoveries', 
                       'Total Deductions', 'Net Salary'] and float(value) > 0:
            # Truncate long names for better fit
            short_name = key[:10] + "..." if len(key) > 10 else key
            deductions.append((short_name, value))
    
    # Get totals from salary service
    total_earnings = float(salary_data.get('Total Earnings', 0))
    total_deductions = float(salary_data.get('Total Deductions', 0))
    net_salary = float(salary_data.get('Net Salary', 0))
    
    # Truncate employee name if too long
    employee_name = salary_data.get('Employee Name', '')
    if len(employee_name) > 25:
        employee_name = employee_name[:22] + "..."
    
    html = f"""
    <div class="payslip">
        <div class="header">
            <h2>SSPL CONSTRUCTIONS PVT LTD</h2>
            <p>PAYSLIP FOR {month_name} {year}</p>
        </div>
        
        <div class="employee-info">
            <div class="left-info">
                <p><strong>ID:</strong> {salary_data.get('Employee ID', '')}</p>
                <p><strong>Name:</strong> {employee_name}</p>
                <p><strong>Skill:</strong> {salary_data.get('Skill Level', '')[:10]}</p>
                <p><strong>Days:</strong> {salary_data.get('Present Days', 0)}</p>
            </div>
            <div class="right-info">
                <p><strong>Dept:</strong> {(employee.department.department_name if employee and employee.department else 'N/A')[:12]}</p>
                <p><strong>Desig:</strong> {(employee.designation if employee else 'N/A')[:10]}</p>
                <p><strong>Rate:</strong> ₹{format_amount(salary_data.get('Daily Wage', 0))}</p>
                <p><strong>Site:</strong> {(employee.site_id if employee else 'N/A')[:10]}</p>
            </div>
        </div>
        
        <div class="salary-details">
            <div class="earnings">
                <h4>EARNINGS</h4>
                <table>
    """
    
    # Limit earnings display to prevent overflow
    display_earnings = earnings[:6]  # Show maximum 6 items
    for name, amount in display_earnings:
        html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>₹{format_amount(amount)}</td>
                    </tr>
        """
    
    html += f"""
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td><strong>₹{format_amount(total_earnings)}</strong></td>
                    </tr>
                </table>
            </div>
            
            <div class="deductions">
                <h4>DEDUCTIONS</h4>
                <table>
    """
    
    # Limit deductions display to prevent overflow
    display_deductions = deductions[:6]  # Show maximum 6 items
    for name, amount in display_deductions:
        html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>₹{format_amount(amount)}</td>
                    </tr>
        """
    
    html += f"""
                    <tr class="total-row">
                        <td><strong>TOTAL</strong></td>
                        <td><strong>₹{format_amount(total_deductions)}</strong></td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="net-salary">
            <div class="net-amount">
                <p><strong>NET SALARY: ₹{format_amount(net_salary)}</strong></p>
            </div>
            <div class="amount-words">
                <p><strong>{number_to_words(int(net_salary))} Only</strong></p>
            </div>
        </div>
        
        <div class="signature">
            <div class="employee-signature">
                <p>Employee Signature</p>
                <div class="signature-line"></div>
            </div>
            <div class="employer-signature">
                <p>Employer Signature</p>
                <div class="signature-line"></div>
            </div>
        </div>
    </div>
    """
    
    return html


def generate_payslips_css():
    """Generate server-compatible CSS for payslip layout (3 per page)"""
    return """
    <style>
        @page {
            size: A4;
            margin: 8mm;
        }
        
        body {
            font-family: 'DejaVu Sans', 'Liberation Sans', Arial, Helvetica, sans-serif !important;
            font-size: 10px;
            line-height: 1.2;
            margin: 0;
            padding: 0;
            color: #000;
            background: white;
        }
        
        .payslip {
            width: 100%;
            height: 32%;
            margin-bottom: 2mm;
            border: 1px solid #000;
            padding: 2mm;
            box-sizing: border-box;
            page-break-inside: avoid;
            background: white;
            position: relative;
        }
        
        .payslip:last-child {
            margin-bottom: 0;
        }
        
        /* Force page breaks every 3 payslips */
        .payslip:nth-child(3n) {
            page-break-after: always;
            margin-bottom: 0;
        }
        
        .payslip:nth-child(3n):last-child {
            page-break-after: auto;
        }
        
        .header {
            text-align: center;
            border-bottom: 1.5px solid #000;
            margin-bottom: 3mm;
            padding-bottom: 2mm;
        }
        
        .header h2 {
            margin: 0;
            font-size: 13px;
            font-weight: bold;
            line-height: 1.1;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .header p {
            margin: 1mm 0 0 0;
            font-size: 10px;
            font-weight: bold;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .employee-info {
            width: 100%;
            margin-bottom: 3mm;
            border-bottom: 1px solid #ccc;
            padding-bottom: 2mm;
            overflow: hidden;
        }
        
        .left-info {
            width: 48%;
            float: left;
        }
        
        .right-info {
            width: 48%;
            float: right;
        }
        
        .employee-info p {
            margin: 0.5mm 0;
            font-size: 9px;
            line-height: 1.1;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .salary-details {
            width: 100%;
            margin-bottom: 3mm;
            overflow: hidden;
        }
        
        .earnings {
            width: 48%;
            float: left;
            margin-right: 2%;
        }
        
        .deductions {
            width: 48%;
            float: right;
            margin-left: 2%;
        }
        
        .earnings h4, .deductions h4 {
            margin: 0 0 2mm 0;
            font-size: 10px;
            text-align: center;
            background-color: #f0f0f0;
            padding: 1mm;
            border: 1px solid #ccc;
            font-weight: bold;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .earnings table, .deductions table {
            width: 100%;
            border-collapse: collapse;
            font-size: 8px;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .earnings td, .deductions td {
            padding: 0.5mm 1mm;
            border: 1px solid #ccc;
            line-height: 1.1;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .earnings td:first-child, .deductions td:first-child {
            text-align: left;
            width: 60%;
        }
        
        .earnings td:last-child, .deductions td:last-child {
            text-align: right;
            width: 40%;
        }
        
        .total-row td {
            background-color: #f0f0f0;
            font-weight: bold;
            font-size: 9px;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .net-salary {
            text-align: center;
            margin-bottom: 3mm;
            border: 1.5px solid #000;
            padding: 2mm;
            background-color: #f9f9f9;
            clear: both;
        }
        
        .net-amount {
            font-size: 11px;
            font-weight: bold;
            margin-bottom: 1mm;
            line-height: 1.1;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .amount-words {
            font-size: 8px;
            font-style: italic;
            line-height: 1.1;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .signature {
            width: 100%;
            margin-top: 2mm;
            overflow: hidden;
        }
        
        .employee-signature {
            width: 45%;
            float: left;
            text-align: center;
        }
        
        .employer-signature {
            width: 45%;
            float: right;
            text-align: center;
        }
        
        .signature p {
            margin: 0 0 8mm 0;
            font-size: 8px;
            font-family: 'DejaVu Sans', Arial, sans-serif !important;
        }
        
        .signature-line {
            border-bottom: 1px solid #000;
            width: 100%;
            height: 1px;
        }
        
        /* Clear floats */
        .payslip::after,
        .employee-info::after,
        .salary-details::after,
        .signature::after {
            content: "";
            display: table;
            clear: both;
        }
        
        /* Print optimizations */
        @media print {
            .payslip {
                break-inside: avoid;
            }
            
            * {
                font-family: 'DejaVu Sans', Arial, sans-serif !important;
            }
        }
    </style>
    """

def detect_server_environment():
    """Detect if running in server environment and log details"""
    import platform
    import sys
    
    env_info = {
        'platform': platform.platform(),
        'python_version': sys.version,
        'pdf_generator': PDF_GENERATOR,
        'available_fonts': []
    }
    
    # Try to detect available fonts
    try:
        import subprocess
        result = subprocess.run(['fc-list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            fonts = result.stdout.split('\n')[:10]  # First 10 fonts
            env_info['available_fonts'] = fonts
    except:
        env_info['available_fonts'] = ['Font detection failed']
    
    logger.info(f"Server environment: {env_info}")
    return env_info
    


def generate_pdf_from_html(html_content: str, filename: str) -> str:
    """Generate PDF using pdf_service"""
    return generate_payroll_pdf(html_content, filename)

@payroll_bp.route('/preview', methods=['GET'])
@token_required
@require_admin_or_supervisor
def preview_payroll(current_user):
    """Preview payroll for selected employees (first 3 only)"""
    try:
        # Get parameters
        employee_ids = request.args.get('employee_ids', '').split(',')
        employee_ids = [int(id.strip()) for id in employee_ids if id.strip().isdigit()]
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not employee_ids:
            return jsonify({'success': False, 'message': 'No valid employee IDs provided'}), 400
        
        if not start_date or not end_date:
            return jsonify({'success': False, 'message': 'Start date and end date are required'}), 400
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # For simplicity, use the start date's month and year
        year = start_dt.year
        month = start_dt.month
        
        # Get employees (limit to first 3 for preview)
        preview_employee_ids = employee_ids[:3]
        employees = Employee.query.filter(Employee.employee_id.in_(preview_employee_ids)).all()
        
        if not employees:
            return jsonify({'success': False, 'message': 'No employees found'}), 404
        
        # Generate HTML preview
        html_content = generate_payslips_css()
        html_content += "<body>"
        
        for employee in employees:
            try:
                employee_data = {
                    'Employee ID': employee.employee_id,
                    'Employee Name': f"{employee.first_name} {employee.last_name}"
                }
                payslip_html = generate_payslip_html(employee_data, year, month)
                html_content += payslip_html
            except Exception as emp_error:
                print(f"Error generating payslip for employee {employee.employee_id}: {str(emp_error)}")
                html_content += f"<div>Error generating payslip for {employee.first_name} {employee.last_name}: {str(emp_error)}</div>"
        
        html_content += "</body>"
        
        return jsonify({
            'success': True,
            'message': 'Preview generated successfully',
            'data': {
                'preview_html': html_content,
                'total_employees': len(employee_ids),
                'preview_count': len(employees),
                'period': f"{start_date} to {end_date}"
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error generating preview', 'error': str(e)}), 500

@payroll_bp.route('/generate', methods=['POST'])
@token_required
@require_admin_or_supervisor
def generate_payroll(current_user):
    """Generate and download payroll PDF"""
    try:
        data = request.get_json()
        
        # Handle different selection modes
        employee_ids = []
        
        if 'employee_ids' in data:
            employee_ids = data['employee_ids']
        elif 'employee_range' in data:
            range_data = data['employee_range']
            from_id = range_data.get('from')
            to_id = range_data.get('to')
            
            if from_id and to_id:
                # Get all employees in range
                employees_in_range = Employee.query.filter(
                    Employee.employee_id >= from_id,
                    Employee.employee_id <= to_id
                ).all()
                employee_ids = [emp.employee_id for emp in employees_in_range]
        
        if not employee_ids:
            return jsonify({'success': False, 'message': 'No employees selected'}), 400
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        filename = data.get('filename', f'payslip_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        if not start_date or not end_date:
            return jsonify({'success': False, 'message': 'Start date and end date are required'}), 400
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # For simplicity, use the start date's month and year
        year = start_dt.year
        month = start_dt.month
        
        # Get employees
        employees = Employee.query.filter(Employee.employee_id.in_(employee_ids)).all()
        
        if not employees:
            return jsonify({'success': False, 'message': 'No employees found'}), 404
        
        # Generate complete HTML with all payslips
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Payslips</title>
            {generate_payslips_css()}
        </head>
        <body>
        """
        
        for employee in employees:
            try:
                employee_data = {
                    'Employee ID': employee.employee_id,
                    'Employee Name': f"{employee.first_name} {employee.last_name}"
                }
                payslip_html = generate_payslip_html(employee_data, year, month)
                html_content += payslip_html
            except Exception as emp_error:
                # Log individual employee error but continue with others
                print(f"Error generating payslip for employee {employee.employee_id}: {str(emp_error)}")
                html_content += f"<div>Error generating payslip for {employee.first_name} {employee.last_name}: {str(emp_error)}</div>"
        
        html_content += """
        </body>
        </html>
        """
        
        # Check if PDF generation is available
        if PDF_GENERATOR is None:
            # Return HTML as fallback
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename.replace(".pdf", ".html")}"'
            return response
        
        # Generate PDF with better error handling
        try:
            pdf_path = generate_pdf_from_html(html_content, filename)
            
            # Return PDF file
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as pdf_error:
            print(f"PDF generation error: {str(pdf_error)}")
            # Return HTML as fallback
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename.replace(".pdf", ".html")}"'
            return response
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error generating payroll', 'error': str(e)}), 500

@payroll_bp.route('/employees', methods=['GET'])
@token_required
@require_admin_or_supervisor
def get_employees_for_payroll(current_user):
    """Get list of employees for payroll selection"""
    try:
        site_id = request.args.get('site_id')
        
        query = Employee.query.filter_by(employment_status='Active')
        
        # Role-based filtering
        if current_user.role == 'supervisor':
            # Supervisors can only see employees from their assigned site
            if current_user.site_id:
                query = query.filter_by(site_id=current_user.site_id)
            else:
                # If supervisor has no assigned site, return empty list
                return jsonify({
                    'success': True,
                    'message': 'No site assigned to supervisor',
                    'data': []
                })
        elif site_id:
            # For admin/hr/manager, apply site filter if provided
            query = query.filter_by(site_id=site_id)
        
        employees = query.all()
        
        employee_list = []
        for emp in employees:
            employee_list.append({
                'employee_id': emp.employee_id,
                'name': f"{emp.first_name} {emp.last_name}",
                'department': emp.department.department_name if emp.department else 'N/A',
                'site_id': emp.site_id or 'N/A',
                'skill_level': emp.skill_category or 'Un-Skilled'
            })
        
        return jsonify({
            'success': True,
            'message': 'Employees retrieved successfully',
            'data': employee_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error retrieving employees', 'error': str(e)}), 500

@payroll_bp.route('/test', methods=['GET'])
@token_required
@require_admin_or_supervisor
def test_payroll(current_user):
    """Test payroll generation with debugging info"""
    try:
        # Get a test employee
        employee = Employee.query.first()
        if not employee:
            return jsonify({'success': False, 'message': 'No employees found for testing'}), 404
        
        # Test salary calculation
        from datetime import datetime
        current_date = datetime.now()
        salary_result = SalaryService.calculate_individual_salary(
            employee.employee_id, current_date.year, current_date.month
        )
        
        # Test PDF generation with a simple HTML
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .test { border: 1px solid black; padding: 20px; }
            </style>
        </head>
        <body>
            <div class="test">
                <h1>Test PDF Generation</h1>
                <p>This is a test to verify PDF generation is working.</p>
            </div>
        </body>
        </html>
        """
        
        pdf_test_result = "Not tested"
        try:
            pdf_path = generate_pdf_from_html(test_html, "test.pdf")
            pdf_test_result = f"Success: {pdf_path}"
        except Exception as pdf_e:
            pdf_test_result = f"Failed: {str(pdf_e)}"
        
        return jsonify({
            'success': True,
            'message': 'Payroll test completed',
            'data': {
                'pdf_generator': PDF_GENERATOR,
                'employee_id': employee.employee_id,
                'employee_name': f"{employee.first_name} {employee.last_name}",
                'salary_calculation': salary_result,
                'pdf_test': pdf_test_result
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Test failed', 'error': str(e)}), 500

@payroll_bp.route('/sites', methods=['GET'])
@token_required
@require_admin_or_supervisor
def get_sites_for_payroll(current_user):
    """Get list of sites for filtering"""
    try:
        from models.site import Site
        
        # Role-based filtering
        if current_user.role == 'supervisor':
            # Supervisors can only see their assigned site
            if current_user.site_id:
                sites = Site.query.filter_by(site_id=current_user.site_id).all()
            else:
                sites = []
        else:
            # Admin/HR/Manager can see all sites
            sites = Site.query.all()
        
        site_list = []
        for site in sites:
            site_list.append({
                'site_id': site.site_id,
                'site_name': site.site_name or 'Unnamed Site',
                'location': site.location if site.location and str(site.location).lower() not in ['nan', 'null', 'none'] else None
            })
        
        return jsonify({
            'success': True,
            'message': 'Sites retrieved successfully',
            'data': site_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error retrieving sites', 'error': str(e)}), 500
