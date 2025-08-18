from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.wage_master import WageMaster
from models.holiday import Holiday
from datetime import datetime, date
from sqlalchemy import and_, func
import pandas as pd
import calendar

class SalaryService:

    # Wage rates by skill level (fallback mapping - your exact logic)
    wage_map = {
        'Highly Skilled': 868.00,
        'Skilled': 739.00,
        'Semi-Skilled': 614.00,
        'Un-Skilled': 526.00
    }

    @staticmethod
    def get_employee_daily_wage(employee_id):
        """
        Get daily wage for an employee from their salary code
        Falls back to skill level mapping if salary code not found
        """
        try:
            employee = Employee.query.filter_by(employee_id=employee_id).first()

            if not employee:
                return 526.0  # Default to Un-Skilled rate

            # Priority 1: Use wage from salary code (WageMaster)
            if employee.wage_master and employee.wage_master.base_wage:
                return employee.wage_master.base_wage

            # Priority 2: Use direct wage_rate field
            if employee.wage_rate:
                return employee.wage_rate

            # Priority 3: Fallback to skill level mapping
            skill_level = employee.skill_category or 'Un-Skilled'
            return SalaryService.wage_map.get(skill_level, 526.0)

        except Exception as e:
            print(f"Error getting wage for employee {employee_id}: {str(e)}")
            return 526.0  # Default to Un-Skilled rate

    @staticmethod
    def calculate_salary_from_attendance_data(df, adjustments_df=None):
        """
        Calculate salary using your exact logic from the provided code
        Updated to use employee salary codes for wage rates
        """
        try:
            # If adjustments dataframe is provided but empty, create empty DataFrame
            adj = adjustments_df if adjustments_df is not None and not adjustments_df.empty else pd.DataFrame()

            # Identify day-wise columns (your exact logic)
            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            attendance_cols = [col for col in df.columns if any(day in col for day in weekdays)]

            def calculate(row):
                # Your exact calculation logic but get wage from employee's salary code
                days_present = sum(str(row[col]).strip().upper() == 'P' for col in attendance_cols)

                # Get daily wage from employee's salary code
                employee_id = str(row['Employee ID']).strip()
                daily_wage = SalaryService.get_employee_daily_wage(employee_id)

                basic = days_present * daily_wage
                pf = 0.12 * min(basic, 15000)
                esic = 0.0075 * min(basic, 21000)
                return pd.Series([days_present, daily_wage, basic, pf, esic])

            # Apply your exact calculation
            df[['Present Days', 'Daily Wage', 'Basic', 'PF', 'ESIC']] = df.apply(calculate, axis=1)

            # Merge optional adjustments (your exact logic)
            if not adj.empty:
                df = pd.merge(df, adj, on='Employee ID', how='left')

            # Ensure all expected columns exist (your exact logic)
            earnings_cols = ['Special Basic', 'DA', 'HRA', 'Overtime', 'Others']
            deduction_cols = ['Society', 'Income Tax', 'Insurance', 'Others Recoveries']
            for col in earnings_cols + deduction_cols:
                if col not in df.columns:
                    df[col] = 0

            # Calculate totals (your exact logic)
            df['Total Earnings'] = df[['Basic'] + earnings_cols].sum(axis=1)
            df['Total Deductions'] = df[['PF', 'ESIC'] + deduction_cols].sum(axis=1)
            df['Net Salary'] = df['Total Earnings'] - df['Total Deductions']

            # Final clean output (your exact logic)
            final_cols = ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 'Basic'] + \
                         earnings_cols + ['Total Earnings', 'PF', 'ESIC'] + deduction_cols + \
                         ['Total Deductions', 'Net Salary']
            output = df[final_cols].fillna(0).to_dict(orient='records')

            return {
                'success': True,
                'message': 'Salary calculated successfully.',
                'data': output
            }

        except Exception as e:
            return {
                'success': False,
                'message': 'An error occurred while processing the salary calculation.',
                'error': str(e)
            }

    @staticmethod
    def generate_monthly_salary_data(year, month):
        """
        Generate salary calculation data for a specific month using database records
        """
        try:
            # Get all employees
            employees = Employee.query.all()

            if not employees:
                return {
                    'success': False,
                    'message': 'No employees found'
                }

            # Create DataFrame structure for your salary calculation logic
            salary_data = []

            for employee in employees:
                # Get monthly attendance summary
                from services.attendance_service import AttendanceService
                attendance_summary = AttendanceService.get_monthly_attendance_summary(
                    employee.employee_id, year, month
                )

                if not attendance_summary['success']:
                    continue

                summary_data = attendance_summary['data']

                # Create row data matching your expected format
                row_data = {
                    'Employee ID': employee.employee_id,
                    'Employee Name': f"{employee.first_name} {employee.last_name}",
                    'Skill Level': employee.skill_category or 'Un-Skilled',  # Default to Un-Skilled if not set
                }

                # Add day-wise attendance (simplified - using present days for now)
                present_days = summary_data['present_days']
                row_data['Present Days Count'] = present_days

                salary_data.append(row_data)

            # Convert to DataFrame
            df = pd.DataFrame(salary_data)

            if df.empty:
                return {
                    'success': False,
                    'message': 'No salary data to calculate'
                }

            # For this simplified version, we'll calculate directly without day-wise columns
            def calculate_simplified(row):
                days_present = row['Present Days Count']
                employee_id = str(row['Employee ID']).strip()

                # Get daily wage from employee's salary code
                daily_wage = SalaryService.get_employee_daily_wage(employee_id)

                basic = days_present * daily_wage
                pf = 0.12 * min(basic, 15000)
                esic = 0.0075 * min(basic, 21000)
                return pd.Series([days_present, daily_wage, basic, pf, esic])

            df[['Present Days', 'Daily Wage', 'Basic', 'PF', 'ESIC']] = df.apply(calculate_simplified, axis=1)

            # Add default values for earnings and deductions
            earnings_cols = ['Special Basic', 'DA', 'HRA', 'Overtime', 'Others']
            deduction_cols = ['Society', 'Income Tax', 'Insurance', 'Others Recoveries']
            for col in earnings_cols + deduction_cols:
                df[col] = 0

            # Calculate totals
            df['Total Earnings'] = df[['Basic'] + earnings_cols].sum(axis=1)
            df['Total Deductions'] = df[['PF', 'ESIC'] + deduction_cols].sum(axis=1)
            df['Net Salary'] = df['Total Earnings'] - df['Total Deductions']

            # Final output
            final_cols = ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 'Basic'] + \
                         earnings_cols + ['Total Earnings', 'PF', 'ESIC'] + deduction_cols + \
                         ['Total Deductions', 'Net Salary']
            output = df[final_cols].fillna(0).to_dict(orient='records')

            return {
                'success': True,
                'message': 'Salary calculated successfully.',
                'data': output
            }

        except Exception as e:
            return {
                'success': False,
                'message': 'An error occurred while generating salary data.',
                'error': str(e)
            }

    @staticmethod
    def calculate_individual_salary(employee_id, year, month, adjustments=None):
        """
        Calculate salary for a single employee
        """
        try:
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            if not employee:
                return {
                    'success': False,
                    'message': 'Employee not found'
                }

            # Get attendance data
            from services.attendance_service import AttendanceService
            attendance_summary = AttendanceService.get_monthly_attendance_summary(
                employee_id, year, month
            )

            if not attendance_summary['success']:
                return attendance_summary

            summary_data = attendance_summary['data']

            # Calculate using your logic with employee's salary code
            days_present = summary_data['present_days']

            # Get daily wage from employee's salary code
            daily_wage = SalaryService.get_employee_daily_wage(employee_id)

            # Get skill level for display - prioritize employee's skill_category
            if employee.skill_category and employee.skill_category.strip():
                skill_level = employee.skill_category
            elif employee.wage_master and employee.wage_master.skill_level and employee.wage_master.skill_level.strip() and employee.wage_master.skill_level != 'Not Specified':
                skill_level = employee.wage_master.skill_level
            else:
                skill_level = 'Un-Skilled'

            basic = days_present * daily_wage
            pf = 0.12 * min(basic, 15000)
            esic = 0.0075 * min(basic, 21000)

            # Apply adjustments if provided
            special_basic = adjustments.get('Special Basic', 0) if adjustments else 0
            da = adjustments.get('DA', 0) if adjustments else 0
            hra = adjustments.get('HRA', 0) if adjustments else 0
            overtime = adjustments.get('Overtime', 0) if adjustments else 0
            others_earnings = adjustments.get('Others', 0) if adjustments else 0

            society = adjustments.get('Society', 0) if adjustments else 0
            income_tax = adjustments.get('Income Tax', 0) if adjustments else 0
            insurance = adjustments.get('Insurance', 0) if adjustments else 0
            others_recoveries = adjustments.get('Others Recoveries', 0) if adjustments else 0

            total_earnings = basic + special_basic + da + hra + overtime + others_earnings
            total_deductions = pf + esic + society + income_tax + insurance + others_recoveries
            net_salary = total_earnings - total_deductions

            result = {
                'Employee ID': employee_id,
                'Employee Name': f"{employee.first_name} {employee.last_name}",
                'Skill Level': skill_level,
                'Present Days': days_present,
                'Daily Wage': daily_wage,
                'Basic': basic,
                'Special Basic': special_basic,
                'DA': da,
                'HRA': hra,
                'Overtime': overtime,
                'Others': others_earnings,
                'Total Earnings': total_earnings,
                'PF': pf,
                'ESIC': esic,
                'Society': society,
                'Income Tax': income_tax,
                'Insurance': insurance,
                'Others Recoveries': others_recoveries,
                'Total Deductions': total_deductions,
                'Net Salary': net_salary
            }

            return {
                'success': True,
                'message': 'Salary calculated successfully.',
                'data': result
            }

        except Exception as e:
            return {
                'success': False,
                'message': 'An error occurred while calculating salary.',
                'error': str(e)
            }