from flask import Blueprint, request, jsonify
from services.salary_service import SalaryService
import pandas as pd
import io
from openpyxl.styles import NamedStyle

salary_bp = Blueprint("salary", __name__)

@salary_bp.route("/upload", methods=["POST"])
def upload_excel():
    """
    Your exact salary calculation logic - unchanged
    Upload Excel files for attendance and adjustments, calculate salary
    """
    file = request.files.get('attendance')
    adjustments = request.files.get('adjustments')

    try:
        # Read attendance Excel file
        df = pd.read_excel(file)

        # Read adjustments Excel file if provided
        adj = pd.read_excel(adjustments) if adjustments else pd.DataFrame()

        # Use your exact calculation logic
        result = SalaryService.calculate_salary_from_attendance_data(df, adj)

        if result['success']:
            return jsonify({
                'message': result['message'],
                'data': result['data']
            })
        else:
            return jsonify({
                "message": result['message'],
                "error": result.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "message": "An error occurred while processing the file.",
            "error": str(e)
        }), 500

@salary_bp.route("/calculate-monthly", methods=["POST"])
def calculate_monthly_salary():
    """
    Calculate salary for all employees for a specific month using database records
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        year = data.get('year')
        month = data.get('month')
        site_id = data.get('site_id')  # Optional site filter

        if not year or not month:
            return jsonify({
                "success": False,
                "message": "Year and month are required"
            }), 400

        # Generate salary data using database records
        result = SalaryService.generate_monthly_salary_data(year, month, site_id)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error calculating monthly salary: {str(e)}"
        }), 500

@salary_bp.route("/calculate-individual", methods=["POST"])
def calculate_individual_salary():
    """
    Calculate salary for a single employee
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400

        employee_id = data.get('employee_id')
        year = data.get('year')
        month = data.get('month')
        adjustments = data.get('adjustments', {})

        if not employee_id or not year or not month:
            return jsonify({
                "success": False,
                "message": "Employee ID, year, and month are required"
            }), 400

        # Calculate individual salary
        result = SalaryService.calculate_individual_salary(
            employee_id, year, month, adjustments
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error calculating individual salary: {str(e)}"
        }), 500

@salary_bp.route("/template/attendance", methods=["GET"])
def download_attendance_template():
    """
    Download Excel template for attendance data
    """
    try:
        # Create sample attendance template
        template_data = {
            'Employee ID': ['EMP001', 'EMP002', 'EMP003'],
            'Employee Name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'Skill Level': ['Highly Skilled', 'Skilled', 'Semi-Skilled'],
            'Monday': ['P', 'P', 'A'],
            'Tuesday': ['P', 'P', 'P'],
            'Wednesday': ['P', 'A', 'P'],
            'Thursday': ['P', 'P', 'P'],
            'Friday': ['P', 'P', 'P'],
            'Saturday': ['P', 'A', 'P'],
            'Sunday': ['A', 'A', 'A'],
            'Note': ['Wage rates are fetched from employee salary codes', '', '']
        }

        df = pd.DataFrame(template_data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Attendance', index=False)

        output.seek(0)

        return output.getvalue(), 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=attendance_template.xlsx'
        }

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating template: {str(e)}"
        }), 500

@salary_bp.route("/template/adjustments", methods=["GET"])
def download_adjustments_template():
    """
    Download Excel template for salary adjustments
    """
    try:
        # Create sample adjustments template
        template_data = {
            'Employee ID': ['EMP001', 'EMP002', 'EMP003'],
            'Special Basic': [1000, 1500, 800],
            'DA': [500, 600, 400],
            'HRA': [2000, 2500, 1800],
            'Overtime': [1200, 800, 1000],
            'Others': [300, 200, 150],
            'Society': [100, 150, 80],
            'Income Tax': [2000, 2500, 1500],
            'Insurance': [500, 600, 400],
            'Others Recoveries': [200, 100, 150]
        }

        df = pd.DataFrame(template_data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Adjustments', index=False)

        output.seek(0)

        return output.getvalue(), 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=adjustments_template.xlsx'
        }

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error generating template: {str(e)}"
        }), 500

@salary_bp.route("/export", methods=["POST"])
def export_salary_data():
    """
    Export calculated salary data to Excel with proper formatting
    """
    try:
        data = request.get_json()

        if not data or not data.get('salary_data'):
            return jsonify({
                "success": False,
                "message": "No salary data provided"
            }), 400

        salary_data = data['salary_data']

        # Handle both single record (dict) and multiple records (list of dicts)
        if isinstance(salary_data, dict):
            # Single salary record - wrap in list for DataFrame
            salary_data = [salary_data]

        # Convert to DataFrame
        df = pd.DataFrame(salary_data)

        # Define expected column order for better readability
        expected_columns = [
            'Employee ID', 'Employee Name', 'Skill Level', 'Present Days',
            'Basic', 'Special Basic', 'DA', 'HRA', 'Overtime', 'Overtime Allowance',
            'Clothes', 'Others', 'Total Earnings',
            'PF', 'ESIC', 'Society', 'Income Tax', 'Insurance', 'Others Recoveries',
            'Total Deductions', 'Net Salary'
        ]

        # Reorder columns if they exist in the data
        existing_columns = [col for col in expected_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in existing_columns]
        final_columns = existing_columns + remaining_columns

        df = df[final_columns]

        # Format numeric columns
        numeric_columns = [
            'Basic', 'Special Basic', 'DA', 'HRA', 'Overtime', 'Overtime Allowance',
            'Clothes', 'Others', 'Total Earnings', 'PF', 'ESIC', 'Society',
            'Income Tax', 'Insurance', 'Others Recoveries', 'Total Deductions', 'Net Salary'
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

        # Create Excel file in memory with better formatting
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Salary Report', index=False)

            # Get the workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Salary Report']

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                adjusted_width = min(max_length + 2, 50)  # Max width of 50
                worksheet.column_dimensions[column_letter].width = adjusted_width

            # Format numeric columns
            currency_style = NamedStyle(name='currency', number_format='#,##0.00')

            for col_num, column_title in enumerate(df.columns, 1):
                if column_title in numeric_columns:
                    for row_num in range(2, len(df) + 2):  # Start from row 2 (after header)
                        cell = worksheet.cell(row=row_num, column=col_num)
                        cell.style = currency_style

        output.seek(0)

        return output.getvalue(), 200, {
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=salary_report.xlsx'
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error exporting salary data: {str(e)}"
        }), 500