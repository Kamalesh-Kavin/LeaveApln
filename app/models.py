import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
import requests
import certifi
from dotenv import load_dotenv
import os

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
    leave_requests = relationship("LeaveRequest", back_populates="user")

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    user = relationship("User", back_populates="leave_requests")
    channel_id = db.Column(db.String(50), nullable=True)
    message_ts = db.Column(db.String(50), nullable=True)
