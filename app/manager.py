from .models import db, User, LeaveRequest, LeaveStatus
from .slack_bot import send_message_from_manager, update_message

from app.models import db, User, LeaveRequest

def fetch_intern_users():
    intern_users = User.query.filter_by(role='Intern').all()  # Modify this query based on your data model
    return intern_users

def format_intern_users_for_modal(intern_users):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*List of Intern Users:*"
            }
        },
        {"type": "divider"}
    ]
    for user in intern_users:
        blocks.append({
            "type": "section",
            "block_id": f"user_{user.id}",
            "text": {
                "type": "mrkdwn",
                "text": (f"*Slack ID:* {user.slack_id}\n"
                         f"*User Name:* {user.name}\n"
                         f"*User ID:* {user.id}\n"
                         f"*No. of leaves remaining:* {user.leave_balance}")
            }
        })
    return blocks

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
    
def view_all_pending_leaves_ui():
    pending_leaves = LeaveRequest.query.filter_by(status=LeaveStatus.PENDING).all()

    if not pending_leaves:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "No long pending leave requests found."
            }
        }]
    
    blocks = []
    for leave in pending_leaves:
        user = User.query.get(leave.user_id)
        leave_id = leave.id
        user_name = user.name
        start_date = leave.start_date.strftime('%Y-%m-%d')
        end_date = leave.end_date.strftime('%Y-%m-%d')
        reason = leave.reason
        
        # Section block with leave details
        blocks.append({
            "type": "section",
            "block_id": f"pending_leave_{leave_id}",
            "text": {
                "type": "mrkdwn",
                "text": (f"*User:* {user_name}\n"
                         f"*Start Date:* {start_date}\n"
                         f"*End Date:* {end_date}\n"
                         f"*Reason:* {reason}")
            }
        })

        # Actions block with approve and decline buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Approve"
                    },
                    "action_id": "approve",
                    "value": str(leave_id)
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Decline"
                    },
                    "action_id": "decline",
                    "value": str(leave_id)
                }
            ]
        })
    
    return blocks

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

def view_intern_leave_history(user_id):
    intern = User.query.filter_by(id=user_id).first()
    if not intern:
        return "Intern not found."
    leave_requests = LeaveRequest.query.filter_by(user_id=intern.id).all()
    if not leave_requests:
        return f"No leave history found for {intern.name}."
    leave_history = [f"Leave ID: {lr.id} - From {lr.start_date} to {lr.end_date}: {lr.status}" for lr in leave_requests]
    return "\n".join(leave_history)

def handle_interactive_message(payload):
    try:
        actions = payload.get('actions', [])
        if not actions:
            return "No actions found in the payload."
        action = actions[0] 
        action_id = action.get('action_id')
        print(action_id)
        value = action.get('value')
        leave_id = int(value)
        print(leave_id)
        channel_id = payload.get('channel', {}).get('id')
        message_ts = payload.get('message', {}).get('ts')
        if not channel_id or not message_ts:
            leave_request = LeaveRequest.query.filter_by(id=leave_id).one()
            channel_id = leave_request.channel_id
            message_ts = leave_request.message_ts
        print(channel_id, message_ts)
        if action_id in ['approve', 'decline']:
            action_type = 'approve' if action_id == 'approve' else 'decline'
            # Call the function to approve or decline
            response = approve_or_decline_leave(payload['user']['id'], leave_id, action_type)
            updated_text = f"Leave request {leave_id} has been {action_type}d by <@{payload['user']['id']}>."
            updated_blocks = [
                {
                    "type": "section",
                    "block_id": "section-identifier",
                    "text": {
                        "type": "mrkdwn",
                        "text": updated_text
                    }
                },
                {
                    "type": "section",
                    "block_id": "status-identifier",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Status:* {'Approved' if action_id == 'approve' else 'Declined'}"
                    }
                }
            ]
            update_message(channel_id, message_ts, updated_text, updated_blocks)
            return response
        else:
            return "Unknown action."
    except Exception as e:
        return f"An error occurred: {e}"
