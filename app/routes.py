from flask import Blueprint, request, jsonify
from .intern import apply_leave, view_leave_status, cancel_leave_request, view_past_leaves, view_leave_balance
from .manager import approve_or_decline_leave, view_intern_leave_history

bp = Blueprint('routes', __name__)

@bp.route('/')
def home():
    return "Welcome to the Leave Bot Application!"

@bp.route('/slack/leave', methods=['POST'])
def handle_leave():
    data = request.form
    user_id = data.get('user_id')
    command = data.get('command')
    text = data.get('text')

    if command == '/applyleave':
        try:
            start_date, end_date, reason = text.split(" ", 2)
            response = apply_leave(user_id, start_date, end_date, reason)
        except ValueError:
            response = "Please provide the start date, end date, and reason in the format: 'start_date end_date reason'."

    elif command == '/leavestatus':
        response = view_leave_status(user_id)

    elif command == '/cancelleave':
        try:
            leave_id = int(text)
            response = cancel_leave_request(user_id, leave_id)
        except ValueError:
            response = "Please provide a valid leave ID to cancel."

    elif command == '/pastleaves':
        response = view_past_leaves(user_id)

    elif command == '/leavebalance':
        response = view_leave_balance(user_id)

    elif command in ['/approve', '/decline']:
        try:
            leave_id = int(text)
            response = approve_or_decline_leave(leave_id, command.strip('/'))
        except ValueError:
            response = "Please provide a valid leave ID."

    elif command == '/leavehistory':
        intern_id = text.strip()
        response = view_intern_leave_history(intern_id)

    else:
        response = "Unknown command."

    return jsonify(response_type='ephemeral', text=response)

def register_routes(app):
    app.register_blueprint(bp)