from .models import db, User, LeaveRequest, LeaveStatus
from .slack_bot import send_message_from_manager

from app.models import db, User

def create_manager(slack_id, name):
    try:
        user = User.query.filter_by(slack_id=slack_id).first()
        if user:
            return "User already exists."
        new_manager = User(slack_id=slack_id, name=name, role="Manager")
        db.session.add(new_manager)
        db.session.commit()

        return f"Manager user created successfully: {name} (Slack ID: {slack_id})"
    
    except Exception as e:
        return f"An error occurred: {e}"

def view_all_pending_leaves():
    pending_leaves = LeaveRequest.query.filter_by(status=LeaveStatus.PENDING).all()
    if not pending_leaves:
        return "No pending leave requests found."

    response = "Pending leave requests:\n"
    for index, leave in enumerate(pending_leaves, start=1):
        user = User.query.get(leave.user_id)
        response += (f"{index}. Leave ID: {leave.id} - User: {user.name} - "
                     f"From {leave.start_date} to {leave.end_date} - Reason: {leave.reason}\n")
    return response

def approve_or_decline_leave(user_id, leave_id, action):
    try:
        manager = User.query.filter_by(slack_id=user_id, role='Manager').first()
        if not manager:
            return "Only managers can approve or decline leave requests."

        leave_request = LeaveRequest.query.filter_by(id=leave_id).first()
        if not leave_request:
            return "Leave request not found."
        leave_days = (leave_request.end_date - leave_request.start_date).days + 1
        intern = leave_request.user
        if action.lower() == 'approve':
            leave_request.status = LeaveStatus.APPROVED
        elif action.lower() == 'decline':
            leave_request.status = LeaveStatus.DECLINED
            intern.leave_balance = min(intern.leave_balance + leave_days, 2)
        else:
            return "Invalid action. Please specify 'approve' or 'decline'."
        db.session.commit()
        # Notify the intern
        send_message_from_manager(leave_request.user.slack_id, f"Your leave request from {leave_request.start_date} to {leave_request.end_date} has been {leave_request.status.value.lower()}.")

        return f"Leave request has been {leave_request.status.value.lower()}."

    except Exception as e:
        return f"An error occurred: {e}"


def view_intern_leave_history(intern_name):
    intern = User.query.filter(User.name.ilike(f"%{intern_name}%"), User.role == 'Intern').first()
    if not intern:
        return "Intern not found."
    leave_requests = LeaveRequest.query.filter_by(user_id=intern.id).all()
    if not leave_requests:
        return f"No leave history found for {intern.name}."
    leave_history = [f"Leave ID: {lr.id} - From {lr.start_date} to {lr.end_date}: {lr.status}" for lr in leave_requests]
    return "\n".join(leave_history)


def handle_interactive_message(payload):
    try:
        # Extract action and value from the payload
        actions = payload.get('actions', [])
        if not actions:
            return "No actions found in the payload."
        action = actions[0]  # Assuming a single action for simplicity
        action_id = action.get('action_id')
        print(action_id)
        value = action.get('value')
        # Extract leave_id and action type
        if action_id in ['approve', 'decline']:
            print("here")
            # Extract leave_id from the original text or payload
            leave_id = int(payload.get('message', {}).get('text', '').split()[0])
            print(leave_id)
            if action_id == 'approve':
                action = 'approve'
            elif action_id == 'decline':
                action = 'decline'
            
            # Call the function to approve or decline
            response = approve_or_decline_leave(payload['user']['id'], leave_id, action)
            return response
        else:
            return "Unknown action."
    except Exception as e:
        return f"An error occurred: {e}"
