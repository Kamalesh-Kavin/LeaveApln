import enum
from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class LeaveStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    DECLINED = "Declined"
    CANCELLED = "Cancelled"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slack_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Intern')  # 'intern' or 'manager'
    leave_balance = db.Column(db.Integer, default=2)  # leave balance for the current month
    last_reset_month = db.Column(db.String(7), nullable=False, default='')  # format YYYY-MM
    leave_requests = relationship("LeaveRequest", back_populates="user")

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    user = relationship("User", back_populates="leave_requests")
