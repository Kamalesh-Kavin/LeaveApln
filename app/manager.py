from .models import db, User, LeaveRequest
from .slack_bot import send_message

def approve_or_decline_leave(leave_id, action):
    leave_request = LeaveRequest.query.filter_by(id=leave_id).first()
    if not leave_request:
        return "Leave request not found."

    if action.lower() == 'approve':
        leave_request.status = 'approved'
        # Deduct leave days from intern's balance
        leave_days = (leave_request.end_date - leave_request.start_date).days + 1
        leave_request.user.leave_balance -= leave_days
    elif action.lower() == 'decline':
        leave_request.status = 'declined'
    else:
        return "Invalid action. Please specify 'approve' or 'decline'."

    db.session.commit()

    # Notify the intern
    send_message(leave_request.user.slack_id, f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {leave_request.status}.")

    return f"Leave request has been {leave_request.status}."

def view_intern_leave_history(intern_id):
    user = User.query.filter_by(slack_id=intern_id, role='intern').first()
    if not user:
        return "Intern not found."
    
    leave_requests = LeaveRequest.query.filter_by(user_id=user.id).all()
    leave_history = [f"Leave from {lr.start_date} to {lr.end_date}: {lr.status}" for lr in leave_requests]
    return "\n".join(leave_history)
