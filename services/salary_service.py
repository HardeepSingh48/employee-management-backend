from models import db
from models.employee import Employee
from models.attendance import Attendance
from models.wage_master import WageMaster
from models.holiday import Holiday
from models.deduction import Deduction
from datetime import datetime, date
from sqlalchemy import and_, func, case
import pandas as pd
import calendar

class SalaryService:

    # Wage rates by skill level (fallback mapping)
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
                return 526.0

            if employee.wage_master and employee.wage_master.base_wage:
                return employee.wage_master.base_wage

            if employee.wage_rate:
                return employee.wage_rate

            skill_level = employee.skill_category or 'Un-Skilled'
            return SalaryService.wage_map.get(skill_level, 526.0)

        except Exception as e:
            print(f"Error getting wage for employee {employee_id}: {str(e)}")
            return 526.0

    @staticmethod
    def get_monthly_deductions(employee_id, year, month):
        """
        Get monthly deductions for an employee for a specific month
        Returns (total_deduction, deduction_details_dict)
        """
        try:
            deductions = Deduction.query.filter_by(employee_id=employee_id).all()
            
            total_deduction = 0
            deduction_details = {}
            
            for deduction in deductions:
                if deduction.is_active_for_month(year, month):
                    installment = deduction.get_installment_for_month(year, month)
                    total_deduction += installment
                    
                    deduction_type = deduction.deduction_type
                    if deduction_type in deduction_details:
                        deduction_details[deduction_type] += installment
                    else:
                        deduction_details[deduction_type] = installment
            
            return float(total_deduction or 0), deduction_details
            
        except Exception as e:
            print(f"Error getting deductions for employee {employee_id}: {str(e)}")
            return 0.0, {}

    @staticmethod
    def generate_monthly_salary_data(year, month, site_id=None):
        """
        OPTIMIZED: Generate salary calculation data using bulk queries
        Reduces from N*3 queries to 3-4 total queries
        """
        try:
            # Import models at function level to avoid scoping issues
            from models.wage_master import WageMaster
            from models.site import Site

            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            # ============================================
            # STEP 1: Get all employees with wage data in ONE JOIN query
            # ============================================

            if site_id:
                # When filtering by site, we need to join through WageMaster and Site
                employees_query = db.session.query(
                    Employee.employee_id,
                    Employee.first_name,
                    Employee.last_name,
                    Employee.skill_category,
                    Employee.salary_code,
                    Employee.wage_rate,
                    WageMaster.base_wage.label('wage_master_base_wage')
                ).join(
                    WageMaster, Employee.salary_code == WageMaster.salary_code
                ).join(
                    Site, WageMaster.site_name == Site.site_name
                ).filter(Site.site_id == site_id)
            else:
                # When getting all employees, use outer join to include employees without wage masters
                employees_query = db.session.query(
                    Employee.employee_id,
                    Employee.first_name,
                    Employee.last_name,
                    Employee.skill_category,
                    Employee.salary_code,
                    Employee.wage_rate,
                    WageMaster.base_wage.label('wage_master_base_wage')
                ).outerjoin(
                    WageMaster,
                    Employee.salary_code == WageMaster.salary_code
                )

            employees_data = employees_query.all()

            if not employees_data:
                return {'success': False, 'message': f'No employees found{" for site " + site_id if site_id else ""}'}
            
            # Create employee lookup dictionary with wage calculation
            employee_dict = {}
            for emp in employees_data:
                # Calculate daily wage using the same priority logic
                if emp.wage_master_base_wage:
                    daily_wage = emp.wage_master_base_wage
                elif emp.wage_rate:
                    daily_wage = emp.wage_rate
                else:
                    skill_level = emp.skill_category or 'Un-Skilled'
                    daily_wage = SalaryService.wage_map.get(skill_level, 526.0)
                
                # Calculate overtime rate (not stored in Employee model, calculated from daily wage)
                overtime_rate_hourly = daily_wage / 8
                
                employee_dict[emp.employee_id] = {
                    'employee_id': emp.employee_id,
                    'name': f"{emp.first_name} {emp.last_name}",
                    'skill_category': emp.skill_category or 'Un-Skilled',
                    'daily_wage': daily_wage,
                    'overtime_rate_hourly': overtime_rate_hourly
                }
            
            employee_ids = list(employee_dict.keys())
            
            # ============================================
            # STEP 2: Bulk fetch ALL attendance data in ONE aggregated query
            # ============================================
            attendance_summary = db.session.query(
                Attendance.employee_id,
                func.count(case((Attendance.attendance_status.in_(['Present', 'Late']), 1))).label('present_days'),
                func.count(case((Attendance.attendance_status == 'Absent', 1))).label('absent_days'),
                func.count(case((Attendance.attendance_status == 'Late', 1))).label('late_days'),
                func.count(case((Attendance.attendance_status == 'Half Day', 1))).label('half_days'),
                func.coalesce(func.sum(Attendance.overtime_shifts), 0).label('total_overtime_shifts')
            ).filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).group_by(
                Attendance.employee_id
            ).all()
            
            # Create attendance lookup dictionary
            attendance_dict = {
                record.employee_id: {
                    'present_days': record.present_days or 0,
                    'absent_days': record.absent_days or 0,
                    'late_days': record.late_days or 0,
                    'half_days': record.half_days or 0,
                    'total_overtime_shifts': float(record.total_overtime_shifts or 0)
                }
                for record in attendance_summary
            }
            
            # ============================================
            # STEP 3: Bulk fetch ALL deductions in ONE query
            # ============================================
            all_deductions = Deduction.query.filter(
                Deduction.employee_id.in_(employee_ids)
            ).all()
            
            # Group deductions by employee
            deductions_by_employee = {}
            for deduction in all_deductions:
                if deduction.is_active_for_month(year, month):
                    emp_id = deduction.employee_id
                    if emp_id not in deductions_by_employee:
                        deductions_by_employee[emp_id] = []
                    deductions_by_employee[emp_id].append(deduction)
            
            # ============================================
            # STEP 4: Calculate salary for all employees (in-memory)
            # ============================================
            salary_data = []
            
            for emp_id, emp_info in employee_dict.items():
                # Get attendance data (default to zeros if no records)
                attendance = attendance_dict.get(emp_id, {
                    'present_days': 0,
                    'absent_days': 0,
                    'late_days': 0,
                    'half_days': 0,
                    'total_overtime_shifts': 0
                })
                
                # Calculate basic salary components
                present_days = attendance['present_days']
                daily_wage = emp_info['daily_wage']
                basic = present_days * daily_wage
                
                # Calculate statutory deductions
                pf = round(0.12 * min(basic, 15000), 2)
                esic = round(0.0075 * min(basic, 21000), 2)
                
                # Calculate overtime
                overtime_shifts = attendance['total_overtime_shifts']
                overtime_hours = overtime_shifts * 8
                overtime_allowance = round(overtime_hours * emp_info['overtime_rate_hourly'], 2)
                
                # Get monthly deductions
                monthly_deduction_total = 0
                deduction_details = {}
                
                if emp_id in deductions_by_employee:
                    for deduction in deductions_by_employee[emp_id]:
                        installment = deduction.get_installment_for_month(year, month)
                        monthly_deduction_total += installment
                        
                        deduction_type = deduction.deduction_type
                        if deduction_type in deduction_details:
                            deduction_details[deduction_type] += installment
                        else:
                            deduction_details[deduction_type] = installment
                
                # Initialize other components
                special_basic = 0
                da = 0
                hra = 0
                overtime_manual = 0
                others_earnings = 0
                society = 0
                income_tax = 0
                insurance = 0
                others_recoveries = 0
                
                # Calculate totals
                total_earnings = basic + special_basic + da + hra + overtime_manual + overtime_allowance + others_earnings
                total_deductions = pf + esic + society + income_tax + insurance + others_recoveries + monthly_deduction_total
                net_salary = total_earnings - total_deductions
                
                # Build result dictionary
                result = {
                    'Employee ID': emp_id,
                    'Employee Name': emp_info['name'],
                    'Skill Level': emp_info['skill_category'],
                    'Present Days': present_days,
                    'Daily Wage': round(daily_wage, 2),
                    'Basic': round(basic, 2),
                    'Special Basic': round(special_basic, 2),
                    'DA': round(da, 2),
                    'HRA': round(hra, 2),
                    'Overtime': round(overtime_manual, 2),
                    'Overtime Allowance': round(overtime_allowance, 2),
                    'Others': round(others_earnings, 2),
                    'Total Earnings': round(total_earnings, 2),
                    'PF': round(pf, 2),
                    'ESIC': round(esic, 2),
                    'Society': round(society, 2),
                    'Income Tax': round(income_tax, 2),
                    'Insurance': round(insurance, 2),
                    'Others Recoveries': round(others_recoveries, 2),
                    'Total Deductions': round(total_deductions, 2),
                    'Net Salary': round(net_salary, 2)
                }
                
                # Add dynamic deduction details
                for deduction_type, amount in deduction_details.items():
                    result[deduction_type] = round(amount, 2)
                
                salary_data.append(result)
            
            return {
                'success': True,
                'message': f'Salary calculated successfully for {len(salary_data)} employees.',
                'data': salary_data
            }
            
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {
                'success': False,
                'message': 'An error occurred while generating salary data.',
                'error': str(e)
            }

    @staticmethod
    def calculate_salary_from_attendance_data(df, adjustments_df=None):
        """
        Calculate salary using attendance data from Excel upload
        """
        try:
            adj = adjustments_df if adjustments_df is not None and not adjustments_df.empty else pd.DataFrame()

            weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            attendance_cols = [col for col in df.columns if any(day in col for day in weekdays)]

            def calculate(row):
                days_present = sum(str(row[col]).strip().upper() == 'P' for col in attendance_cols)
                employee_id = str(row['Employee ID']).strip()
                daily_wage = SalaryService.get_employee_daily_wage(employee_id)

                basic = days_present * daily_wage
                pf = 0.12 * min(basic, 15000)
                esic = 0.0075 * min(basic, 21000)
                return pd.Series([days_present, daily_wage, basic, pf, esic])

            df[['Present Days', 'Daily Wage', 'Basic', 'PF', 'ESIC']] = df.apply(calculate, axis=1)

            if not adj.empty:
                df = pd.merge(df, adj, on='Employee ID', how='left')

            earnings_cols = ['Special Basic', 'DA', 'HRA', 'Overtime', 'Overtime Allowance', 'Others']
            deduction_cols = ['Society', 'Income Tax', 'Insurance', 'Others Recoveries']
            for col in earnings_cols + deduction_cols:
                if col not in df.columns:
                    df[col] = 0

            for index, row in df.iterrows():
                employee_id = str(row['Employee ID']).strip()
                
                current_date = datetime.now()
                year = current_date.year
                month = current_date.month
                
                employee = Employee.query.filter_by(employee_id=employee_id).first()
                
                from services.attendance_service import AttendanceService
                attendance_summary = AttendanceService.get_monthly_attendance_summary(
                    employee_id, year, month
                )
                
                if attendance_summary['success']:
                    summary_data = attendance_summary['data']
                    total_overtime_shifts = summary_data.get('total_overtime_shifts', 0)
                    total_overtime_hours = total_overtime_shifts * 8
                    
                    if employee and hasattr(employee, 'overtime_rate_hourly') and employee.overtime_rate_hourly:
                        overtime_rate_hourly = employee.overtime_rate_hourly
                    else:
                        daily_wage = row['Daily Wage']
                        overtime_rate_hourly = daily_wage / 8
                    
                    overtime_allowance = total_overtime_hours * overtime_rate_hourly
                    
                    df.at[index, 'Overtime Allowance'] = overtime_allowance
                    df.at[index, 'Overtime Shifts'] = total_overtime_shifts
                    df.at[index, 'Overtime Hours'] = total_overtime_hours
                    df.at[index, 'Overtime Rate Hourly'] = overtime_rate_hourly
                
                monthly_deduction_total, deduction_details = SalaryService.get_monthly_deductions(employee_id, year, month)
                
                for deduction_type, amount in deduction_details.items():
                    if deduction_type not in df.columns:
                        df[deduction_type] = 0
                    df.at[index, deduction_type] = amount

            df['Total Earnings'] = df[['Basic'] + earnings_cols].sum(axis=1)
            df['Total Deductions'] = df[['PF', 'ESIC'] + deduction_cols].sum(axis=1)
            
            for index, row in df.iterrows():
                employee_id = str(row['Employee ID']).strip()
                current_date = datetime.now()
                year = current_date.year
                month = current_date.month
                
                monthly_deduction_total, _ = SalaryService.get_monthly_deductions(employee_id, year, month)
                df.at[index, 'Total Deductions'] += monthly_deduction_total
            
            df['Net Salary'] = df['Total Earnings'] - df['Total Deductions']

            deduction_type_cols = [col for col in df.columns if col not in ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 'Basic'] + 
                                 earnings_cols + ['Total Earnings', 'PF', 'ESIC'] + deduction_cols + ['Total Deductions', 'Net Salary']]
            
            final_cols = ['Employee ID', 'Employee Name', 'Skill Level', 'Present Days', 'Daily Wage', 'Basic'] + \
                         earnings_cols + ['Total Earnings', 'PF', 'ESIC'] + deduction_cols + deduction_type_cols + \
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

            from services.attendance_service import AttendanceService
            attendance_summary = AttendanceService.get_monthly_attendance_summary(
                employee_id, year, month
            )

            if not attendance_summary['success']:
                return attendance_summary

            summary_data = attendance_summary['data']
            days_present = summary_data['present_days']
            daily_wage = SalaryService.get_employee_daily_wage(employee_id)

            if employee.skill_category and employee.skill_category.strip():
                skill_level = employee.skill_category
            elif employee.wage_master and employee.wage_master.skill_level and employee.wage_master.skill_level.strip() and employee.wage_master.skill_level != 'Not Specified':
                skill_level = employee.wage_master.skill_level
            else:
                skill_level = 'Un-Skilled'

            basic = days_present * daily_wage
            pf = 0.12 * min(basic, 15000)
            esic = 0.0075 * min(basic, 21000)
            
            overtime_allowance, total_overtime_shifts, total_overtime_hours, overtime_rate_hourly = SalaryService.calculate_overtime_allowance(
                employee_id, year, month
            )

            special_basic = adjustments.get('Special Basic', 0) if adjustments else 0
            da = adjustments.get('DA', 0) if adjustments else 0
            hra = adjustments.get('HRA', 0) if adjustments else 0
            overtime = adjustments.get('Overtime', 0) if adjustments else 0
            others_earnings = adjustments.get('Others', 0) if adjustments else 0

            society = adjustments.get('Society', 0) if adjustments else 0
            income_tax = adjustments.get('Income Tax', 0) if adjustments else 0
            insurance = adjustments.get('Insurance', 0) if adjustments else 0
            others_recoveries = adjustments.get('Others Recoveries', 0) if adjustments else 0

            total_earnings = basic + special_basic + da + hra + overtime + overtime_allowance + others_earnings
            total_deductions = pf + esic + society + income_tax + insurance + others_recoveries
            
            monthly_deduction_total, deduction_details = SalaryService.get_monthly_deductions(employee_id, year, month)
            total_deductions += monthly_deduction_total
            
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
                'Overtime Allowance': overtime_allowance,
                'Overtime Shifts': total_overtime_shifts,
                'Overtime Hours': total_overtime_hours,
                'Overtime Rate Hourly': overtime_rate_hourly,
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
            
            for deduction_type, amount in deduction_details.items():
                result[deduction_type] = amount

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

    @staticmethod
    def calculate_overtime_allowance(employee_id, year, month):
        """
        Calculate overtime allowance for an employee using overtime shifts
        Returns: (overtime_allowance, overtime_shifts, overtime_hours, overtime_rate_hourly)
        """
        try:
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            if not employee:
                return 0.0, 0.0, 0.0, 0.0

            from services.attendance_service import AttendanceService
            attendance_summary = AttendanceService.get_monthly_attendance_summary(
                employee_id, year, month
            )

            if not attendance_summary['success']:
                return 0.0, 0.0, 0.0, 0.0

            summary_data = attendance_summary['data']
            total_overtime_shifts = summary_data.get('total_overtime_shifts', 0)
            total_overtime_hours = total_overtime_shifts * 8

            if hasattr(employee, 'overtime_rate_hourly') and employee.overtime_rate_hourly:
                overtime_rate_hourly = employee.overtime_rate_hourly
            else:
                daily_wage = SalaryService.get_employee_daily_wage(employee_id)
                overtime_rate_hourly = daily_wage / 8

            overtime_allowance = total_overtime_hours * overtime_rate_hourly

            return overtime_allowance, total_overtime_shifts, total_overtime_hours, overtime_rate_hourly

        except Exception as e:
            print(f"Error calculating overtime allowance for employee {employee_id}: {str(e)}")
            return 0.0, 0.0, 0.0, 0.0

    @staticmethod
    def get_employee_overtime_summary(employee_id, year, month):
        """
        Get detailed overtime summary for an employee
        """
        try:
            overtime_allowance, overtime_shifts, overtime_hours, overtime_rate = SalaryService.calculate_overtime_allowance(
                employee_id, year, month
            )

            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'year': year,
                    'month': month,
                    'overtime_shifts': overtime_shifts,
                    'overtime_hours': overtime_hours,
                    'overtime_rate_hourly': overtime_rate,
                    'overtime_allowance': overtime_allowance
                }
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting overtime summary: {str(e)}'
            }

    @staticmethod
    def calculate_bulk_preview_salaries(employee_ids, year, month):
        """
        OPTIMIZED: Calculate salaries for multiple employees in bulk for preview
        Returns pre-calculated salary data to avoid N+1 queries
        """
        try:
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            # STEP 1: Bulk fetch employee data with wage info (1 query)
            employees_query = db.session.query(
                Employee.employee_id,
                Employee.first_name,
                Employee.last_name,
                Employee.skill_category,
                Employee.salary_code,
                Employee.wage_rate,
                WageMaster.base_wage.label('wage_master_base_wage')
            ).outerjoin(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).filter(
                Employee.employee_id.in_(employee_ids)
            )

            employees_data = employees_query.all()

            # Create employee lookup
            employee_dict = {}
            for emp in employees_data:
                # Calculate daily wage
                if emp.wage_master_base_wage:
                    daily_wage = emp.wage_master_base_wage
                elif emp.wage_rate:
                    daily_wage = emp.wage_rate
                else:
                    skill_level = emp.skill_category or 'Un-Skilled'
                    daily_wage = SalaryService.wage_map.get(skill_level, 526.0)

                overtime_rate_hourly = daily_wage / 8

                employee_dict[emp.employee_id] = {
                    'employee_id': emp.employee_id,
                    'name': f"{emp.first_name or ''} {emp.last_name or ''}".strip() or f"Employee {emp.employee_id}",
                    'skill_category': emp.skill_category or 'Un-Skilled',
                    'daily_wage': daily_wage,
                    'overtime_rate_hourly': overtime_rate_hourly
                }

            # STEP 2: Bulk fetch attendance data (1 query)
            attendance_summary = db.session.query(
                Attendance.employee_id,
                func.count(case((Attendance.attendance_status.in_(['Present', 'Late']), 1))).label('present_days'),
                func.count(case((Attendance.attendance_status == 'Absent', 1))).label('absent_days'),
                func.count(case((Attendance.attendance_status == 'Late', 1))).label('late_days'),
                func.count(case((Attendance.attendance_status == 'Half Day', 1))).label('half_days'),
                func.coalesce(func.sum(Attendance.overtime_shifts), 0).label('total_overtime_shifts')
            ).filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).group_by(
                Attendance.employee_id
            ).all()

            # Create attendance lookup
            attendance_dict = {
                record.employee_id: {
                    'present_days': record.present_days or 0,
                    'absent_days': record.absent_days or 0,
                    'late_days': record.late_days or 0,
                    'half_days': record.half_days or 0,
                    'total_overtime_shifts': float(record.total_overtime_shifts or 0)
                }
                for record in attendance_summary
            }

            # STEP 3: Bulk fetch deductions (1 query)
            all_deductions = Deduction.query.filter(
                Deduction.employee_id.in_(employee_ids)
            ).all()

            # Group deductions by employee
            deductions_by_employee = {}
            for deduction in all_deductions:
                if deduction.is_active_for_month(year, month):
                    emp_id = deduction.employee_id
                    if emp_id not in deductions_by_employee:
                        deductions_by_employee[emp_id] = []
                    deductions_by_employee[emp_id].append(deduction)

            # STEP 4: Calculate salaries in memory
            salary_data_dict = {}

            for emp_id, emp_info in employee_dict.items():
                # Get attendance data
                attendance = attendance_dict.get(emp_id, {
                    'present_days': 0, 'absent_days': 0, 'late_days': 0,
                    'half_days': 0, 'total_overtime_shifts': 0
                })

                # Calculate components
                present_days = attendance['present_days']
                daily_wage = emp_info['daily_wage']
                basic = present_days * daily_wage

                # Statutory deductions
                pf = round(0.12 * min(basic, 15000), 2)
                esic = round(0.0075 * min(basic, 21000), 2)

                # Overtime
                overtime_shifts = attendance['total_overtime_shifts']
                overtime_hours = overtime_shifts * 8
                overtime_allowance = round(overtime_hours * emp_info['overtime_rate_hourly'], 2)

                # Monthly deductions
                monthly_deduction_total = 0
                deduction_details = {}

                if emp_id in deductions_by_employee:
                    for deduction in deductions_by_employee[emp_id]:
                        installment = deduction.get_installment_for_month(year, month)
                        monthly_deduction_total += installment

                        deduction_type = deduction.deduction_type
                        if deduction_type in deduction_details:
                            deduction_details[deduction_type] += installment
                        else:
                            deduction_details[deduction_type] = installment

                # Initialize all components (matching individual calculation)
                special_basic = 0
                da = 0
                hra = 0
                overtime_manual = 0
                others_earnings = 0
                society = 0
                income_tax = 0
                insurance = 0
                others_recoveries = 0

                # Calculate totals (matching individual calculation)
                total_earnings = basic + special_basic + da + hra + overtime_manual + overtime_allowance + others_earnings
                total_deductions = pf + esic + society + income_tax + insurance + others_recoveries + monthly_deduction_total
                net_salary = total_earnings - total_deductions

                # Build salary data structure (matching individual calculation format)
                salary_data_dict[emp_id] = {
                    'Employee ID': emp_id,
                    'Employee Name': emp_info['name'],
                    'Skill Level': emp_info['skill_category'],
                    'Present Days': present_days,
                    'Daily Wage': round(daily_wage, 2),
                    'Basic': round(basic, 2),
                    'Special Basic': round(special_basic, 2),
                    'DA': round(da, 2),
                    'HRA': round(hra, 2),
                    'Overtime': round(overtime_manual, 2),
                    'Overtime Allowance': round(overtime_allowance, 2),
                    'Overtime Shifts': overtime_shifts,
                    'Overtime Hours': overtime_hours,
                    'Overtime Rate Hourly': round(emp_info['overtime_rate_hourly'], 2),
                    'Others': round(others_earnings, 2),
                    'Total Earnings': round(total_earnings, 2),
                    'PF': round(pf, 2),
                    'ESIC': round(esic, 2),
                    'Society': round(society, 2),
                    'Income Tax': round(income_tax, 2),
                    'Insurance': round(insurance, 2),
                    'Others Recoveries': round(others_recoveries, 2),
                    'Total Deductions': round(total_deductions, 2),
                    'Net Salary': round(net_salary, 2),
                    **{k: round(v, 2) for k, v in deduction_details.items()}  # Dynamic deductions
                }

            return {
                'success': True,
                'data': salary_data_dict
            }

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {
                'success': False,
                'message': 'Error in bulk salary calculation',
                'error': str(e)
            }

    @staticmethod
    def calculate_bulk_salaries(employee_ids, year, month):
        """
        OPTIMIZED: Calculate salaries for multiple employees in bulk for PDF generation
        Same as calculate_bulk_preview_salaries but includes all salary components
        """
        try:
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            # STEP 1: Bulk fetch employee data with wage info (1 query)
            employees_query = db.session.query(
                Employee.employee_id,
                Employee.first_name,
                Employee.last_name,
                Employee.skill_category,
                Employee.salary_code,
                Employee.wage_rate,
                WageMaster.base_wage.label('wage_master_base_wage')
            ).outerjoin(
                WageMaster, Employee.salary_code == WageMaster.salary_code
            ).filter(
                Employee.employee_id.in_(employee_ids)
            )

            employees_data = employees_query.all()

            # Create employee lookup
            employee_dict = {}
            for emp in employees_data:
                # Calculate daily wage
                if emp.wage_master_base_wage:
                    daily_wage = emp.wage_master_base_wage
                elif emp.wage_rate:
                    daily_wage = emp.wage_rate
                else:
                    skill_level = emp.skill_category or 'Un-Skilled'
                    daily_wage = SalaryService.wage_map.get(skill_level, 526.0)

                overtime_rate_hourly = daily_wage / 8

                employee_dict[emp.employee_id] = {
                    'employee_id': emp.employee_id,
                    'name': f"{emp.first_name or ''} {emp.last_name or ''}".strip() or f"Employee {emp.employee_id}",
                    'skill_category': emp.skill_category or 'Un-Skilled',
                    'daily_wage': daily_wage,
                    'overtime_rate_hourly': overtime_rate_hourly
                }

            # STEP 2: Bulk fetch attendance data (1 query)
            attendance_summary = db.session.query(
                Attendance.employee_id,
                func.count(case((Attendance.attendance_status.in_(['Present', 'Late']), 1))).label('present_days'),
                func.count(case((Attendance.attendance_status == 'Absent', 1))).label('absent_days'),
                func.count(case((Attendance.attendance_status == 'Late', 1))).label('late_days'),
                func.count(case((Attendance.attendance_status == 'Half Day', 1))).label('half_days'),
                func.coalesce(func.sum(Attendance.overtime_shifts), 0).label('total_overtime_shifts')
            ).filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).group_by(
                Attendance.employee_id
            ).all()

            # Create attendance lookup
            attendance_dict = {
                record.employee_id: {
                    'present_days': record.present_days or 0,
                    'absent_days': record.absent_days or 0,
                    'late_days': record.late_days or 0,
                    'half_days': record.half_days or 0,
                    'total_overtime_shifts': float(record.total_overtime_shifts or 0)
                }
                for record in attendance_summary
            }

            # STEP 3: Bulk fetch deductions (1 query)
            all_deductions = Deduction.query.filter(
                Deduction.employee_id.in_(employee_ids)
            ).all()

            # Group deductions by employee
            deductions_by_employee = {}
            for deduction in all_deductions:
                if deduction.is_active_for_month(year, month):
                    emp_id = deduction.employee_id
                    if emp_id not in deductions_by_employee:
                        deductions_by_employee[emp_id] = []
                    deductions_by_employee[emp_id].append(deduction)

            # STEP 4: Calculate salaries in memory (same as monthly calculation)
            salary_data_dict = {}

            for emp_id, emp_info in employee_dict.items():
                # Get attendance data
                attendance = attendance_dict.get(emp_id, {
                    'present_days': 0, 'absent_days': 0, 'late_days': 0,
                    'half_days': 0, 'total_overtime_shifts': 0
                })

                # Calculate basic salary components (same as generate_monthly_salary_data)
                present_days = attendance['present_days']
                daily_wage = emp_info['daily_wage']
                basic = present_days * daily_wage

                # Statutory deductions
                pf = round(0.12 * min(basic, 15000), 2)
                esic = round(0.0075 * min(basic, 21000), 2)

                # Overtime
                overtime_shifts = attendance['total_overtime_shifts']
                overtime_hours = overtime_shifts * 8
                overtime_allowance = round(overtime_hours * emp_info['overtime_rate_hourly'], 2)

                # Initialize other components (set to 0 for bulk generation)
                special_basic = 0
                da = 0
                hra = 0
                overtime_manual = 0
                others_earnings = 0
                society = 0
                income_tax = 0
                insurance = 0
                others_recoveries = 0

                # Monthly deductions
                monthly_deduction_total = 0
                deduction_details = {}

                if emp_id in deductions_by_employee:
                    for deduction in deductions_by_employee[emp_id]:
                        installment = deduction.get_installment_for_month(year, month)
                        monthly_deduction_total += installment

                        deduction_type = deduction.deduction_type
                        if deduction_type in deduction_details:
                            deduction_details[deduction_type] += installment
                        else:
                            deduction_details[deduction_type] = installment

                # Calculate totals
                total_earnings = basic + special_basic + da + hra + overtime_manual + overtime_allowance + others_earnings
                total_deductions = pf + esic + society + income_tax + insurance + others_recoveries + monthly_deduction_total
                net_salary = total_earnings - total_deductions

                # Build result dictionary (same format as monthly calculation)
                salary_data_dict[emp_id] = {
                    'Employee ID': emp_id,
                    'Employee Name': emp_info['name'],
                    'Skill Level': emp_info['skill_category'],
                    'Present Days': present_days,
                    'Daily Wage': round(daily_wage, 2),
                    'Basic': round(basic, 2),
                    'Special Basic': round(special_basic, 2),
                    'DA': round(da, 2),
                    'HRA': round(hra, 2),
                    'Overtime': round(overtime_manual, 2),
                    'Overtime Allowance': round(overtime_allowance, 2),
                    'Others': round(others_earnings, 2),
                    'Total Earnings': round(total_earnings, 2),
                    'PF': round(pf, 2),
                    'ESIC': round(esic, 2),
                    'Society': round(society, 2),
                    'Income Tax': round(income_tax, 2),
                    'Insurance': round(insurance, 2),
                    'Others Recoveries': round(others_recoveries, 2),
                    'Total Deductions': round(total_deductions, 2),
                    'Net Salary': round(net_salary, 2)
                }

                # Add dynamic deduction details
                for deduction_type, amount in deduction_details.items():
                    salary_data_dict[emp_id][deduction_type] = round(amount, 2)

            return {
                'success': True,
                'data': salary_data_dict
            }

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return {
                'success': False,
                'message': 'Error in bulk salary calculation for PDF',
                'error': str(e)
            }

    @staticmethod
    def get_bulk_monthly_deductions(employee_ids, year, month):
        """
        OPTIMIZED: Get monthly deductions for multiple employees in ONE query
        Returns dict: {employee_id: {total_deduction, deduction_details}}
        """
        try:
            # Single query to get ALL deductions for ALL employees
            all_deductions = Deduction.query.filter(
                Deduction.employee_id.in_(employee_ids)
            ).all()

            # Group deductions by employee
            deductions_by_employee = {}
            for deduction in all_deductions:
                if deduction.is_active_for_month(year, month):
                    emp_id = deduction.employee_id
                    if emp_id not in deductions_by_employee:
                        deductions_by_employee[emp_id] = []
                    deductions_by_employee[emp_id].append(deduction)

            # Calculate totals for each employee
            deductions_dict = {}
            for emp_id in employee_ids:
                monthly_deduction_total = 0
                deduction_details = {}

                if emp_id in deductions_by_employee:
                    for deduction in deductions_by_employee[emp_id]:
                        installment = deduction.get_installment_for_month(year, month)
                        monthly_deduction_total += installment

                        deduction_type = deduction.deduction_type
                        if deduction_type in deduction_details:
                            deduction_details[deduction_type] += installment
                        else:
                            deduction_details[deduction_type] = installment

                deductions_dict[emp_id] = {
                    'total_deduction': float(monthly_deduction_total or 0),
                    'deduction_details': deduction_details
                }

            return {
                'success': True,
                'data': deductions_dict
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error in bulk deductions calculation: {str(e)}'
            }