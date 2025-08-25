from flask import Blueprint, request, jsonify, send_file
from services.salary_service import SalaryService
from models.employee import Employee
from models.wage_master import WageMaster
from models.attendance import Attendance
from models import db
from datetime import datetime, date
import pandas as pd
import io
import calendar

forms_bp = Blueprint("forms", __name__)

@forms_bp.route("/form-b", methods=["GET", "OPTIONS"])
def get_form_b_data():
    """
    Get Form B (Wages Register) data for specified year, month, and site
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Get query parameters
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        site = request.args.get('site')

        if not year or not month:
            return jsonify({
                "success": False,
                "message": "Year and month are required"
            }), 400

        # Get employees for the specified site (if provided)
        query = Employee.query
        if site:
            # Join with WageMaster to filter by site
            query = query.join(WageMaster, Employee.salary_code == WageMaster.salary_code)\
                         .filter(WageMaster.site_name == site)
        
        employees = query.all()

        if not employees:
            return jsonify({
                "success": False,
                "message": "No employees found for the specified criteria"
            }), 404

        form_b_data = []
        
        for idx, employee in enumerate(employees, 1):
            # Calculate salary for this employee
            salary_result = SalaryService.calculate_individual_salary(
                employee.employee_id, year, month
            )
            
            if not salary_result['success']:
                continue
                
            salary_data = salary_result['data']
            
            # Get wage master details
            wage_master = WageMaster.query.filter_by(salary_code=employee.salary_code).first()
            
            # Get attendance summary for the month
            from services.attendance_service import AttendanceService
            attendance_summary = AttendanceService.get_monthly_attendance_summary(
                employee.employee_id, year, month
            )
            
            present_days = 0
            overtime_hours = 0
            if attendance_summary['success']:
                present_days = attendance_summary['data'].get('present_days', 0)
                overtime_hours = attendance_summary['data'].get('total_overtime_hours', 0)
            
            # Calculate overtime amount (assuming 1.5x rate for overtime)
            daily_wage = salary_data.get('Daily Wage', 0)
            overtime_rate = daily_wage / 8 * 1.5  # Hourly overtime rate
            overtime_amount = overtime_hours * overtime_rate
            
            # Map salary data to Form B structure
            form_b_row = {
                "slNo": idx,
                "employeeCode": employee.employee_id,
                "employeeName": f"{employee.first_name} {employee.last_name}",
                "designation": employee.designation or "N/A",
                "rateOfWage": {
                    "bs": wage_master.base_wage if wage_master else daily_wage,
                    "da": 0  # DA component if available in adjustments
                },
                "daysWorked": present_days,
                "overtime": overtime_hours,
                "totalDays": present_days + (overtime_hours / 8),  # Convert OT hours to days
                "grossEarnings": {
                    "bs": salary_data.get('Basic', 0),
                    "da": salary_data.get('DA', 0),
                    "hra": salary_data.get('HRA', 0),
                    "cov": 0,  # Conveyance allowance
                    "ota": overtime_amount,
                    "ae": salary_data.get('Others', 0)  # Additional earnings
                },
                "totalEarnings": salary_data.get('Total Earnings', 0),
                "deductions": {
                    "pf": salary_data.get('PF', 0),
                    "esi": salary_data.get('ESIC', 0),
                    "cit": salary_data.get('Income Tax', 0),
                    "ptax": 0,  # Professional tax
                    "adv": salary_data.get('Others Recoveries', 0),
                    "total": salary_data.get('Total Deductions', 0)
                },
                "netPayable": salary_data.get('Net Salary', 0),
                "siteName": wage_master.site_name if wage_master else "N/A"
            }
            
            form_b_data.append(form_b_row)

        # Calculate totals
        totals = {
            "totalEmployees": len(form_b_data),
            "totalDaysWorked": sum(row["daysWorked"] for row in form_b_data),
            "totalOvertime": sum(row["overtime"] for row in form_b_data),
            "totalEarnings": sum(row["totalEarnings"] for row in form_b_data),
            "totalDeductions": sum(row["deductions"]["total"] for row in form_b_data),
            "totalNetPayable": sum(row["netPayable"] for row in form_b_data)
        }

        return jsonify({
            "success": True,
            "data": form_b_data,
            "totals": totals,
            "filters": {
                "year": year,
                "month": month,
                "site": site,
                "monthName": calendar.month_name[month]
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating Form B data: {str(e)}"
        }), 500


@forms_bp.route("/form-b/download", methods=["GET", "OPTIONS"])
def download_form_b_excel():
    """
    Download Form B data as Excel file
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200

    try:
        # Get query parameters
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        site = request.args.get('site', 'All')

        if not year or not month:
            return jsonify({
                "success": False,
                "message": "Year and month are required"
            }), 400

        # Get Form B data using the same logic as the data endpoint
        form_b_response = get_form_b_data()
        
        if form_b_response[1] != 200:  # Check status code
            return form_b_response
            
        form_b_result = form_b_response[0].get_json()
        form_b_data = form_b_result['data']
        totals = form_b_result['totals']
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Prepare data for Excel
            excel_data = []
            
            for row in form_b_data:
                excel_row = {
                    'Sl.No': row['slNo'],
                    'Employee Code': row['employeeCode'],
                    'Employee Name': row['employeeName'],
                    'Designation': row['designation'],
                    'Rate of Wage (BS)': row['rateOfWage']['bs'],
                    'Rate of Wage (DA)': row['rateOfWage']['da'],
                    'Days Worked': row['daysWorked'],
                    'Overtime': row['overtime'],
                    'Total Days': row['totalDays'],
                    'BS': row['grossEarnings']['bs'],
                    'DA': row['grossEarnings']['da'],
                    'HRA': row['grossEarnings']['hra'],
                    'COV': row['grossEarnings']['cov'],
                    'OTA': row['grossEarnings']['ota'],
                    'AE': row['grossEarnings']['ae'],
                    'Total Earnings': row['totalEarnings'],
                    'PF': row['deductions']['pf'],
                    'ESI': row['deductions']['esi'],
                    'CIT': row['deductions']['cit'],
                    'PTAX': row['deductions']['ptax'],
                    'ADV': row['deductions']['adv'],
                    'Total Deductions': row['deductions']['total'],
                    'Net Payable': row['netPayable']
                }
                excel_data.append(excel_row)
            
            # Add totals row
            totals_row = {
                'Sl.No': '',
                'Employee Code': '',
                'Employee Name': 'TOTAL',
                'Designation': '',
                'Rate of Wage (BS)': '',
                'Rate of Wage (DA)': '',
                'Days Worked': totals['totalDaysWorked'],
                'Overtime': totals['totalOvertime'],
                'Total Days': '',
                'BS': '',
                'DA': '',
                'HRA': '',
                'COV': '',
                'OTA': '',
                'AE': '',
                'Total Earnings': totals['totalEarnings'],
                'PF': '',
                'ESI': '',
                'CIT': '',
                'PTAX': '',
                'ADV': '',
                'Total Deductions': totals['totalDeductions'],
                'Net Payable': totals['totalNetPayable']
            }
            excel_data.append(totals_row)
            
            # Create DataFrame and write to Excel
            df = pd.DataFrame(excel_data)
            df.to_excel(writer, sheet_name='Form B - Wages Register', index=False)
            
            # Get the workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Form B - Wages Register']
            
            # Add header information as requested by user
            worksheet.insert_rows(1, 5)  # Insert 5 rows for headers
            worksheet['A1'] = "Form B"
            worksheet['A2'] = "Format For Wage Register"
            worksheet['A3'] = f"Rate of minimum Wages {datetime.now().strftime('%d/%m/%Y')}"
            worksheet['A4'] = "SSPL"
            worksheet['A5'] = f"Month: {calendar.month_name[month]} {year} | Site: {site}"

            # Style the headers
            from openpyxl.styles import Font, Alignment

            # Make headers bold and centered
            for row in range(1, 6):
                cell = worksheet[f'A{row}']
                cell.font = Font(bold=True, size=12)
                cell.alignment = Alignment(horizontal='center')

            # Merge cells for headers to span across columns
            worksheet.merge_cells('A1:W1')  # Form B
            worksheet.merge_cells('A2:W2')  # Format For Wage Register
            worksheet.merge_cells('A3:W3')  # Rate of minimum wages with date
            worksheet.merge_cells('A4:W4')  # SSPL
            worksheet.merge_cells('A5:W5')  # Month and Site info
        
        output.seek(0)
        
        # Generate filename
        month_name = calendar.month_name[month]
        filename = f"FormB_{site}_{month_name}_{year}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating Excel file: {str(e)}"
        }), 500
