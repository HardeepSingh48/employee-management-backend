from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models to ensure they are registered with SQLAlchemy
from models.employee import Employee
from models.department import Department
from models.account_details import AccountDetails
from models.wage_master import WageMaster
from models.attendance import Attendance
