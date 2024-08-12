from .models import db, User, LeaveRequest
from .slack_bot import send_message
from datetime import datetime, timedelta

def apply_leave(user_id, start_date, end_date, reason):
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        leave_days = (end_date - start_date).days + 1 #remaining leave days
        user = db.session.query(User).filter_by(slack_id=user_id).first()

        if user is None: #first time using bot
            user = User(slack_id=user_id, name="Unknown", role="Intern")
            db.session.add(user)
            db.session.commit()
            return "User record created with default role."

        # Check if leave balance is sufficient
        if user.leave_balance < leave_days:
            return "Insufficient leave balance."

        current_month = start_date.month
        current_year = start_date.year

        leaves_this_month = db.session.query(LeaveRequest).filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.start_date >= datetime(current_year, current_month, 1),
            LeaveRequest.end_date <= datetime(current_year, current_month + 1, 1) - timedelta(days=1)
        ).all()
        
        total_leave_days_this_month = sum(
            (min(leave.end_date, end_date) - max(leave.start_date, start_date)).days + 1
            for leave in leaves_this_month
        )
        
        if total_leave_days_this_month + leave_days > 2:
            return "Leave limit exceeded. You can only take a maximum of 2 days leave per month."

        
        # Add leave request
        leave_request = LeaveRequest(user_id=user.id, start_date=start_date, end_date=end_date, reason=reason)
        db.session.add(leave_request)
        user.leave_balance -= leave_days
        db.session.commit()

        #notify manager 
        manager = User.query.filter_by(role='manager').first()
        if manager:
            send_message(manager.slack_id, f"{user.name} has applied for leave from {start_date} to {end_date}.")
        return f"Leave applied successfully for {leave_days} days."
    
    except ValueError as e:
        return f"Invalid date format. Please use YYYY-MM-DD. Error: {e}"

    except Exception as e:
        return f"An error occurred: {e}"

def view_leave_status(user_id):
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return "User not found."
    leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
    status_messages = [f"Leave from {lr.start_date} to {lr.end_date}: {lr.status}" for lr in leave_requests]
    return "\n".join(status_messages)

def cancel_leave_request(user_id, leave_id):
    try:
        leave_request = LeaveRequest.query.filter_by(id=leave_id, user_id=user_id, status='pending').first()
        if leave_request is None:
            return "Leave request not found."
        if leave_request.status == 'Approved':
            return "Cannot cancel an approved leave request."
        user = db.session.query(User).filter_by(id=leave_request.user_id).first()
        if user is None:
            return "User not found."
        leave_days = (leave_request.end_date - leave_request.start_date).days + 1
        user.leave_balance += leave_days
        db.session.delete(leave_request)
        db.session.commit()
        return "Leave request canceled successfully."
    except Exception as e:
        return f"An error occurred: {e}"

def view_past_leaves(user_id):
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return "User not found."
    
    leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
    past_leaves = [f"Leave from {lr.start_date} to {lr.end_date}: {lr.status}" for lr in leave_requests]
    return "\n".join(past_leaves)

def view_leave_balance(user_id):
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return "User not found."
    
    return f"You have {user.leave_balance} days of leave remaining."
