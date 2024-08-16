import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey
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
    role = db.Column(db.String(20), nullable=False, default='Intern')  
    leave_balance = db.Column(db.Integer, default=2)  
    last_reset_month = db.Column(db.String(7), nullable=False, default='')  
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True,default=1)

    # Relationship to track leave requests made by this user
    leave_requests = relationship("LeaveRequest", back_populates="user", foreign_keys="[LeaveRequest.user_id]")

    # Self-referential relationship to track the manager-intern hierarchy
    managed_interns = relationship("User", backref=db.backref("manager", remote_side=[id]), foreign_keys=[manager_id])

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    
    # Relationship back to the user who made the request
    user = relationship("User", back_populates="leave_requests", foreign_keys=[user_id])

    # Relationship back to the manager overseeing the request
    manager = relationship("User", foreign_keys=[manager_id])
