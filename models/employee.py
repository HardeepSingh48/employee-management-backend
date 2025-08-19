from models import db
from sqlalchemy.sql import func

class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)

    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100))
    address = db.Column(db.String(500))
    adhar_number = db.Column(db.String(20))
    place_of_birth = db.Column(db.String(100))
    marital_status = db.Column(db.String(20), db.CheckConstraint("marital_status IN ('Single', 'Married', 'Divorced', 'Widowed')"))
    date_of_birth = db.Column(db.Date)
    email = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))

    # Employment Information
    hire_date = db.Column(db.Date)
    job_title = db.Column(db.String(100))
    family_details = db.Column(db.String(500))
    department_id = db.Column(db.String(50), db.ForeignKey("departments.department_id"))
    employment_status = db.Column(db.String(20), db.CheckConstraint("employment_status IN ('Active', 'Inactive', 'On Leave')"), default='Active')

    # Additional fields for comprehensive registration
    gender = db.Column(db.String(20))
    nationality = db.Column(db.String(50), default="Indian")
    blood_group = db.Column(db.String(5))
    alternate_contact_number = db.Column(db.String(20))
    pan_card_number = db.Column(db.String(15))
    voter_id_driving_license = db.Column(db.String(50))
    uan = db.Column(db.String(20))
    esic_number = db.Column(db.String(20))

    # Employment Details
    employment_type = db.Column(db.String(50))
    designation = db.Column(db.String(100))
    work_location = db.Column(db.String(100))
    reporting_manager = db.Column(db.String(100))
    base_salary = db.Column(db.Float)
    skill_category = db.Column(db.String(100))
    wage_rate = db.Column(db.Float)

    # Applicability flags
    pf_applicability = db.Column(db.Boolean, default=False)
    esic_applicability = db.Column(db.Boolean, default=False)
    professional_tax_applicability = db.Column(db.Boolean, default=False)

    # Additional Information
    salary_advance_loan = db.Column(db.String(200))
    highest_qualification = db.Column(db.String(100))
    year_of_passing = db.Column(db.String(10))
    additional_certifications = db.Column(db.String(500))
    experience_duration = db.Column(db.String(50))

    # Emergency Contact
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_relationship = db.Column(db.String(50))
    emergency_contact_phone = db.Column(db.String(20))

    # FK to wage master (salary code)
    salary_code = db.Column(db.String(50), db.ForeignKey("wage_masters.salary_code"), nullable=True)

    # Audit fields
    created_date = db.Column(db.Date, server_default=func.current_date())
    created_by = db.Column(db.String(100))
    updated_date = db.Column(db.Date, onupdate=func.current_date())
    updated_by = db.Column(db.String(100))

    # Relationships
    department = db.relationship("Department", backref="employees")
    wage_master = db.relationship("WageMaster", backref="employees", foreign_keys=[salary_code])

    def __repr__(self):
        return f"<Employee {self.employee_id} - {self.first_name} {self.last_name}>"
