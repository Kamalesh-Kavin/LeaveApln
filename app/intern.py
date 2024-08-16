from .models import db, User, LeaveRequest, LeaveStatus
from .slack_bot import send_message_to_manager
from datetime import datetime, timedelta

def apply_leave(user_id, start_date, end_date, reason, user_name):
    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        leave_days = (end_date - start_date).days + 1
    
        user = User.query.filter_by(slack_id=user_id).first()
        if user is None:
            user = User(slack_id=user_id, name=user_name, role="Intern")
            db.session.add(user)
            db.session.commit()

        current_month = datetime.now().strftime('%Y-%m')
        if user.last_reset_month != current_month:
            user.leave_balance = 2  # Reset to 2 days for the new month
            user.last_reset_month = current_month
            db.session.commit()

        if user.leave_balance < leave_days:
            return "Insufficient leave balance."

        current_month_start = datetime.now().replace(day=1)
        leaves_this_month = LeaveRequest.query.filter(
            LeaveRequest.user_id == user.id,
            LeaveRequest.start_date >= current_month_start,
            LeaveRequest.end_date <= datetime.now().replace(day=1) + timedelta(days=31),
            LeaveRequest.status.notin_([LeaveStatus.CANCELLED, LeaveStatus.DECLINED])
        ).all()

        total_leave_days_this_month = sum(
            (min(leave.end_date, end_date) - max(leave.start_date, start_date)).days + 1
            for leave in leaves_this_month
        )

        if total_leave_days_this_month + leave_days > 2:
            return "Leave limit exceeded. You can only take a maximum of 2 days leave per month."

        leave_request = LeaveRequest(user_id=user.id, start_date=start_date, end_date=end_date, reason=reason)
        db.session.add(leave_request)
        user.leave_balance -= leave_days
        db.session.commit()

        #single manager concept for now
        manager = User.query.filter_by(role='Manager').first()
        print()
        print("MANAGERRRR: ",manager)
        if not manager:
            return "Manager not found."
        try:
            print(manager.slack_id)
            send_message_to_manager(manager.slack_id, leave_request.id, f"{user.name} has applied for leave from {start_date} to {end_date}.")
            print("message sent")
        except Exception as e:
            print(f"Error sending message: {e}")

        return (f"Leave applied successfully!\n"
                f"User: {user_name}\n"
                f"Leave Dates: {start_date} to {end_date}\n"
                f"Total Leave Days: {leave_days}\n"
                f"Remaining Leave Balance: {user.leave_balance} days.")

    except ValueError as e:
        return f"Invalid date format. Please use YYYY-MM-DD. Error: {e}"
    except Exception as e:
        return f"An error occurred: {e}"

def view_pending_leaves_ui(user_id):
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return []

    pending_leaves = LeaveRequest.query.filter_by(user_id=user.id, status='PENDING').all()
    if not pending_leaves:
        return [
            {
                "type": "section",
                "block_id": "no_pending_leaves",
                "text": {
                    "type": "plain_text",
                    "text": "You have no pending leave requests."
                }
            }
        ]

    leave_blocks = []
    for leave in pending_leaves:
        leave_blocks.append({
            "type": "section",
            "block_id": f"pending_leave_{leave.id}",
            "text": {
                "type": "mrkdwn",
                "text": f"*Leave ID:* {leave.id}\n*From:* {leave.start_date}\n*To:* {leave.end_date}\n*Reason:* {leave.reason}"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "action_id": f"cancel_{leave.id}",
                "style": "danger"
            }
        })
    return leave_blocks

def view_pending_leaves(user_id):
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return "User not found."
    
    pending_leaves = LeaveRequest.query.filter_by(user_id=user.id, status='PENDING').all()
    if not pending_leaves:
        return "You have no pending leave requests."
    
    response = "Your pending leave requests:\n"
    for index, leave in enumerate(pending_leaves, start=1):
        response += f"{index}. Leave ID: {leave.id} - From {leave.start_date} to {leave.end_date} - Reason: {leave.reason}\n"
    response += "Please use the corresponding Leave ID to cancel a leave request."
    return response

def cancel_leave_request(user_id, leave_id):
    try:
        user = User.query.filter_by(slack_id=user_id).first()
        if user is None:
            return "User not found."

        leave_request = LeaveRequest.query.filter_by(id=leave_id, user_id=user.id, status=LeaveStatus.PENDING).first()
        if leave_request is None:
            return "Leave request not found or not in pending status."

        leave_days = (leave_request.end_date - leave_request.start_date).days + 1
        user.leave_balance += leave_days
        leave_request.status = LeaveStatus.CANCELLED
        db.session.commit()
        
        return f"Leave request (ID: {leave_id}) cancelled successfully. Leave days added back to your balance."

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
