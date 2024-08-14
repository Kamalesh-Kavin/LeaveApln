from flask import Blueprint, request, jsonify
from .intern import apply_leave, cancel_leave_request, view_past_leaves, view_leave_balance, view_pending_leaves
from .manager import approve_or_decline_leave, view_intern_leave_history, view_all_pending_leaves, handle_interactive_message
from .models import User
import json

bp = Blueprint('routes', __name__)

@bp.route('/')
def home():
    return "Welcome to the Leave Bot Application!!"

@bp.route('/slack/interactions', methods=['POST'])
def handle_interactions():
    print("HIII")
    print(request.content_type)
    if request.content_type != 'application/x-www-form-urlencoded':
        return jsonify(error="Unsupported Media Type"), 415
    payload = request.form.get('payload')
    
    if not payload:
        return jsonify(error="No payload found"), 400

    try:
        # Parse the payload JSON string
        data = json.loads(payload)
    except json.JSONDecodeError:
        return jsonify(error="Invalid JSON in payload"), 400

    action_id = data.get('actions', [{}])[0].get('action_id')
    leave_id = data.get('actions', [{}])[0].get('value')
    user_id = data.get('user', {}).get('id')

    print(f"Action ID: {action_id}, Leave ID: {leave_id}, User ID: {user_id}")

    response = handle_interactive_message(data)
    # if action_id == 'approve':
    #     response = approve_or_decline_leave(user_id, int(leave_id), 'approve')
    # elif action_id == 'decline':
    #     response = approve_or_decline_leave(user_id, int(leave_id), 'decline')
    # else:
    #     response = "Unknown action."
    
    return jsonify(response_type='ephemeral', text=response)

@bp.route('/slack/leave', methods=['POST'])
def handle_leave():
    data = request.form
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    command = data.get('command')
    text = data.get('text', '').strip()

    #just to check bot connectivity
    # if request.json.get('type') == 'url_verification':
    #     return jsonify(challenge=request.json.get('challenge'))
    
    if command == '/applyleave':
        try:
            start_date, end_date, reason = text.split(" ", 2)
            response = apply_leave(user_id, start_date, end_date, reason, user_name)
        except ValueError:
            response = "Please provide the start date, end date, and reason in the format: 'start_date end_date reason'."

    elif command == '/pendingleave':
        response = view_pending_leaves(user_id)

    elif command == '/cancelleave':
        if text == "":
            response = view_pending_leaves(user_id)
        else:
            try:
                selection_number = int(text)
                response = cancel_leave_request(user_id, selection_number)
            except ValueError:
                response = "Please provide a valid number corresponding to the leave you want to cancel."

    elif command == '/pastleaves':
        response = view_past_leaves(user_id)

    elif command == '/leavebalance':
        response = view_leave_balance(user_id)

    elif command in ['/approve', '/decline']:
        try:
            leave_id = int(text.split()[0]) 
            action = command.strip('/') 
            response = approve_or_decline_leave(user_id, leave_id, action)
        except ValueError:
            response = "Please provide a valid leave ID."

    elif command == '/leavehistory':
        intern_name = text.strip()
        response = view_intern_leave_history(intern_name)

    elif command == '/viewpendingleaves':
        manager = User.query.filter_by(slack_id=user_id, role='Manager').first()
        if not manager:
            response = "You must be a manager to view pending leave requests."
        else:
            response = view_all_pending_leaves()

    else:
        response = "Unknown command."

    return jsonify(response_type='ephemeral', text=response)

def register_routes(app):
    app.register_blueprint(bp)