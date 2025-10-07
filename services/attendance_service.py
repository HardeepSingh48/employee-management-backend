from models import db
from models.attendance import Attendance
from models.employee import Employee
from models.holiday import Holiday
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError
import calendar

class AttendanceService:
    
    # @staticmethod
    # def mark_attendance(employee_id, attendance_date, attendance_status,
    #                    check_in_time=None, check_out_time=None,
    #                    overtime_shifts=0.0, remarks=None, marked_by='employee'):
    #     """
    #     Mark attendance for an employee on a specific date
    #     """
    #     try:
    #         # Check if employee exists
    #         employee = Employee.query.filter_by(employee_id=employee_id).first()
    #         if not employee:
    #             return {"success": False, "message": "Employee not found"}

    #         # Parse attendance_date if it's a string
    #         if isinstance(attendance_date, str):
    #             attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()

    #         # Check if attendance already exists for this date
    #         existing_attendance = Attendance.query.filter_by(
    #             employee_id=employee_id,
    #             attendance_date=attendance_date
    #         ).first()

    #         if existing_attendance:
    #             return {"success": False, "message": "Attendance already marked for this date"}

    #         # Check if it's a holiday
    #         is_holiday_date, holiday = Holiday.is_holiday(attendance_date)

    #         # Check if it's weekend
    #         is_weekend = attendance_date.weekday() >= 5  # Saturday = 5, Sunday = 6

    #         # Calculate work hours and lateness
    #         total_hours_worked = 8.0  # Default
    #         late_minutes = 0

    #         if check_in_time and check_out_time:
    #             total_hours_worked = Attendance.calculate_work_hours(check_in_time, check_out_time)
    #             is_late, late_minutes = Attendance.is_late(check_in_time)

    #             # Adjust status if late
    #             if is_late and attendance_status == 'Present':
    #                 attendance_status = 'Late'

    #         # Create attendance record
    #         attendance = Attendance(
    #             employee_id=employee_id,
    #             attendance_date=attendance_date,
    #             check_in_time=check_in_time,
    #             check_out_time=check_out_time,
    #             attendance_status=attendance_status,
    #             overtime_shifts=overtime_shifts,
    #             late_minutes=late_minutes,
    #             total_hours_worked=total_hours_worked,
    #             is_holiday=is_holiday_date,
    #             is_weekend=is_weekend,
    #             remarks=remarks,
    #             marked_by=marked_by,
    #             created_by=marked_by
    #         )

    #         db.session.add(attendance)
    #         db.session.commit()

    #         return {
    #             "success": True,
    #             "message": "Attendance marked successfully",
    #             "data": attendance.to_dict()
    #         }

    #     except IntegrityError:
    #         db.session.rollback()
    #         return {"success": False, "message": "Attendance already exists for this date"}
    #     except Exception as e:
    #         db.session.rollback()
    #         return {"success": False, "message": f"Error marking attendance: {str(e)}"}

    @staticmethod
    def mark_or_update_attendance(employee_id, attendance_date, attendance_status,
                               check_in_time=None, check_out_time=None,
                               overtime_shifts=0.0, remarks=None, marked_by='employee'):
        """
        Mark attendance OR update if already exists
        Returns: dict with 'created' flag to indicate if new record or update
        """
        try:
            # Check if employee exists
            employee = Employee.query.filter_by(employee_id=employee_id).first()
            if not employee:
                return {"success": False, "message": "Employee not found"}

            # Parse attendance_date if string
            if isinstance(attendance_date, str):
                attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()

            # Query for existing attendance record with employee_id + attendance_date
            existing_attendance = Attendance.query.filter_by(
                employee_id=employee_id,
                attendance_date=attendance_date
            ).first()

            # Calculate: is_holiday, is_weekend, total_hours_worked, late_minutes
            is_holiday_date, holiday = Holiday.is_holiday(attendance_date)
            is_weekend = attendance_date.weekday() >= 5  # Saturday = 5, Sunday = 6

            total_hours_worked = 8.0  # Default
            late_minutes = 0

            if check_in_time and check_out_time:
                total_hours_worked = Attendance.calculate_work_hours(check_in_time, check_out_time)
                is_late, late_minutes = Attendance.is_late(check_in_time)

                # Adjust status if late
                if is_late and attendance_status == 'Present':
                    attendance_status = 'Late'

            # Adjust total_hours_worked based on status
            if attendance_status == 'Half Day':
                total_hours_worked = 4.0
            elif attendance_status == 'Absent':
                total_hours_worked = 0.0
            # For Present/Late, keep calculated or default 8.0

            if existing_attendance:
                # UPDATE existing record
                existing_attendance.check_in_time = check_in_time
                existing_attendance.check_out_time = check_out_time
                existing_attendance.attendance_status = attendance_status
                existing_attendance.overtime_shifts = overtime_shifts
                existing_attendance.late_minutes = late_minutes
                existing_attendance.total_hours_worked = total_hours_worked
                existing_attendance.is_holiday = is_holiday_date
                existing_attendance.is_weekend = is_weekend
                existing_attendance.remarks = remarks
                existing_attendance.marked_by = marked_by
                existing_attendance.updated_by = marked_by
                existing_attendance.updated_date = datetime.now()

                db.session.commit()

                return {
                    "success": True,
                    "message": "Attendance updated successfully",
                    "created": False,
                    "data": existing_attendance.to_dict()
                }
            else:
                # CREATE new Attendance object
                attendance = Attendance(
                    employee_id=employee_id,
                    attendance_date=attendance_date,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    attendance_status=attendance_status,
                    overtime_shifts=overtime_shifts,
                    late_minutes=late_minutes,
                    total_hours_worked=total_hours_worked,
                    is_holiday=is_holiday_date,
                    is_weekend=is_weekend,
                    remarks=remarks,
                    marked_by=marked_by,
                    created_by=marked_by
                )

                db.session.add(attendance)
                db.session.commit()

                return {
                    "success": True,
                    "message": "Attendance marked successfully",
                    "created": True,
                    "data": attendance.to_dict()
                }

        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error marking/updating attendance: {str(e)}"}
    
    @staticmethod
    def bulk_mark_attendance(attendance_records, marked_by='admin'):
        """
        Mark attendance for multiple employees
        attendance_records: List of dicts with employee_id, date, status, etc.
        """
        results = []
        successful_count = 0
        
        for record in attendance_records:
            result = AttendanceService.mark_attendance(
                employee_id=record.get('employee_id'),
                attendance_date=record.get('attendance_date'),
                attendance_status=record.get('attendance_status', 'Present'),
                check_in_time=record.get('check_in_time'),
                check_out_time=record.get('check_out_time'),
                overtime_shifts=record.get('overtime_shifts', 0.0),
                remarks=record.get('remarks'),
                marked_by=marked_by
            )
            
            results.append({
                "employee_id": record.get('employee_id'),
                "result": result
            })
            
            if result["success"]:
                successful_count += 1
        
        return {
            "success": True,
            "message": f"Processed {len(attendance_records)} records. {successful_count} successful.",
            "results": results,
            "successful_count": successful_count,
            "total_count": len(attendance_records)
        }
    
    @staticmethod
    def get_employee_attendance(employee_id, start_date=None, end_date=None):
        """
        Get attendance records for an employee within date range
        """
        try:
            query = Attendance.query.filter_by(employee_id=employee_id)
            
            if start_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.attendance_date >= start_date)
            
            if end_date:
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Attendance.attendance_date <= end_date)
            
            attendance_records = query.order_by(Attendance.attendance_date.desc()).all()
            
            return {
                "success": True,
                "data": [record.to_dict() for record in attendance_records],
                "count": len(attendance_records)
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error fetching attendance: {str(e)}"}
    
    @staticmethod
    def get_attendance_by_date(attendance_date):
        """
        Get all attendance records for a specific date
        """
        try:
            if isinstance(attendance_date, str):
                attendance_date = datetime.strptime(attendance_date, '%Y-%m-%d').date()

            # Optimized query: only load necessary employee columns
            attendance_records = Attendance.query.filter_by(
                attendance_date=attendance_date
            ).join(Employee).all()

            results = []
            for record in attendance_records:
                data = record.to_dict()
                # Optimize employee name construction
                first_name = record.employee.first_name or ""
                last_name = record.employee.last_name or ""
                data['employee_name'] = f"{first_name} {last_name}".strip() or record.employee.employee_id
                results.append(data)

            return {
                "success": True,
                "data": results,
                "count": len(results),
                "date": attendance_date.isoformat()
            }

        except Exception as e:
            return {"success": False, "message": f"Error fetching attendance: {str(e)}"}
    
    @staticmethod
    def get_monthly_attendance_summary(employee_id, year, month):
        """
        Get monthly attendance summary for salary calculation - OPTIMIZED VERSION
        Uses database aggregation and parallel queries for better performance
        """
        try:
            # Get first and last day of the month
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            # OPTIMIZATION: Use database aggregation instead of Python loops
            from sqlalchemy import func, case

            # Single optimized query for summary stats using database aggregation
            summary_result = db.session.query(
                func.count(case((Attendance.attendance_status.in_(['Present', 'Late']), 1))).label('present_days'),
                func.count(case((Attendance.attendance_status == 'Absent', 1))).label('absent_days'),
                func.count(case((Attendance.attendance_status == 'Late', 1))).label('late_days'),
                func.count(case((Attendance.attendance_status == 'Half Day', 1))).label('half_days'),
                func.sum(Attendance.overtime_shifts).label('total_overtime_shifts'),
                func.count(Attendance.attendance_id).label('total_records')
            ).filter(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).first()

            # Separate query for daily records (needed for calendar view)
            daily_records = Attendance.query.filter(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).order_by(Attendance.attendance_date).all()

            # Extract summary values
            present_days = summary_result.present_days or 0
            absent_days = summary_result.absent_days or 0
            late_days = summary_result.late_days or 0
            half_days = summary_result.half_days or 0
            total_overtime_shifts = summary_result.total_overtime_shifts or 0.0
            total_overtime_hours = total_overtime_shifts * 8

            # Get holidays in the month (cached calculation)
            holidays = Holiday.get_holidays_for_month(year, month)
            holiday_count = len(holidays)

            # Calculate working days (excluding weekends and holidays) - OPTIMIZED
            working_days = 0
            current_date = first_day
            while current_date <= last_day:
                if current_date.weekday() < 5:  # Monday to Friday
                    is_holiday_date, _ = Holiday.is_holiday(current_date)
                    if not is_holiday_date:
                        working_days += 1
                current_date += timedelta(days=1)

            # Calculate attendance rate
            attendance_percentage = round((present_days / working_days * 100), 2) if working_days > 0 else 0

            return {
                "success": True,
                "data": {
                    "employee_id": employee_id,
                    "year": year,
                    "month": month,
                    "present_days": present_days,
                    "absent_days": absent_days,
                    "late_days": late_days,
                    "half_days": half_days,
                    "total_overtime_shifts": total_overtime_shifts,
                    "total_overtime_hours": total_overtime_hours,
                    "working_days": working_days,
                    "holiday_count": holiday_count,
                    "attendance_percentage": attendance_percentage,
                    "records": [record.to_dict() for record in daily_records]
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error calculating monthly summary: {str(e)}"}

    @staticmethod
    def get_bulk_monthly_attendance_summary(employee_ids, year, month):
        """
        OPTIMIZED: Get monthly attendance summary for multiple employees in ONE query
        Returns dict: {employee_id: {present_days, total_overtime_hours, ...}}
        """
        try:
            # Get first and last day of the month
            first_day = date(year, month, 1)
            last_day = date(year, month, calendar.monthrange(year, month)[1])

            # Single optimized query for ALL employees using database aggregation
            from sqlalchemy import func, case

            summary_results = db.session.query(
                Attendance.employee_id,
                func.count(case((Attendance.attendance_status.in_(['Present', 'Late']), 1))).label('present_days'),
                func.count(case((Attendance.attendance_status == 'Absent', 1))).label('absent_days'),
                func.count(case((Attendance.attendance_status == 'Late', 1))).label('late_days'),
                func.count(case((Attendance.attendance_status == 'Half Day', 1))).label('half_days'),
                func.coalesce(func.sum(Attendance.overtime_shifts), 0).label('total_overtime_shifts'),
                func.count(Attendance.attendance_id).label('total_records')
            ).filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.attendance_date >= first_day,
                Attendance.attendance_date <= last_day
            ).group_by(
                Attendance.employee_id
            ).all()

            # Convert to lookup dictionary
            attendance_dict = {}
            for record in summary_results:
                attendance_dict[record.employee_id] = {
                    'present_days': record.present_days or 0,
                    'absent_days': record.absent_days or 0,
                    'late_days': record.late_days or 0,
                    'half_days': record.half_days or 0,
                    'total_overtime_shifts': float(record.total_overtime_shifts or 0),
                    'total_overtime_hours': float(record.total_overtime_shifts or 0) * 8,
                    'total_records': record.total_records or 0
                }

            # Fill in missing employees with zeros
            for emp_id in employee_ids:
                if emp_id not in attendance_dict:
                    attendance_dict[emp_id] = {
                        'present_days': 0,
                        'absent_days': 0,
                        'late_days': 0,
                        'half_days': 0,
                        'total_overtime_shifts': 0.0,
                        'total_overtime_hours': 0.0,
                        'total_records': 0
                    }

            return {
                'success': True,
                'data': attendance_dict
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error in bulk attendance calculation: {str(e)}'
            }

    @staticmethod
    def update_attendance(attendance_id, **kwargs):
        """
        Update existing attendance record
        """
        try:
            attendance = Attendance.query.get(attendance_id)
            if not attendance:
                return {"success": False, "message": "Attendance record not found"}
            
            # Update allowed fields
            allowed_fields = ['attendance_status', 'check_in_time', 'check_out_time', 
                            'overtime_shifts', 'remarks', 'is_approved', 'approved_by']
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(attendance, field):
                    setattr(attendance, field, value)
            
            attendance.updated_date = datetime.now()
            attendance.updated_by = kwargs.get('updated_by', 'system')
            
            db.session.commit()
            
            return {
                "success": True,
                "message": "Attendance updated successfully",
                "data": attendance.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Error updating attendance: {str(e)}"}
