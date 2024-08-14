from flask import Blueprint, request, jsonify
from .intern import apply_leave, cancel_leave_request, view_past_leaves, view_leave_balance, view_pending_leaves, view_pending_leaves_ui
from .manager import approve_or_decline_leave, view_intern_leave_history, view_all_pending_leaves, handle_interactive_message
from .models import User
import json
import requests
import os

bp = Blueprint('routes', __name__)
slack_token = os.getenv("SLACK_BOT_TOKEN")
print(slack_token)
slack_token="xoxb-7584405679664-7561620439074-lHgAfJv2WjE2PDK3RTpJf74m"

@bp.route('/')
def home():
    return "Welcome to the Leave Bot Application!!"

@bp.route('/slack/apps_home', methods=['POST'])
def app_home():
    print("HOME UI Loading...")
    data = request.json
    print()
    print(data)
    user_id = data.get('event', {}).get('user') or data.get('event', {}).get('message', {}).get('user') or data.get('event', {}).get('edited', {}).get('user')
    if not user_id:
        return jsonify({"status": "error", "message": "User ID not found"}), 400
    user = User.query.filter_by(slack_id=user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    is_intern = user.role == 'Intern'
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hello, How can I help you today?"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Apply leave",
                        "emoji": True
                    },
                    "action_id": "apply_leave",
                    "style": "primary"  # Green button
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View leave history",
                        "emoji": True
                    },
                    "action_id": "view_leave_history"
                }
            ]
        }
    ]
    if is_intern:
        pending_leaves_blocks = view_pending_leaves_ui(user_id)
        blocks.append({
            "type": "section",
            "block_id": "pending_leaves_header",
            "text": {
                "type": "plain_text",
                "text": "Pending Leaves"
            }
        })
        blocks.extend(pending_leaves_blocks)

    # Send the updated home view to Slack
    response = requests.post(
        'https://slack.com/api/views.publish',
        headers={
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        },
        json={
            'user_id': user_id,
            'view': {
                'type': 'home',
                'blocks': blocks
            }
        }
    )
    
    print(f"Slack API response: {response.status_code}, {response.text}")
    if response.status_code != 200:
        return jsonify({"status": "error", "message": response.text}), response.status_code
    return jsonify({"status": "ok"})

# def app_home():
#     print("HOME UI Loading...")
#     data = request.json
#     print()
#     print(data)
#     if 'user' in data.get('event', {}):
#         user_id = data['event']['user']
#     elif 'message' in data.get('event', {}):
#         user_id = data['event']['message'].get('user', None)
#     elif 'edited' in data.get('event', {}):
#         user_id = data['event']['edited'].get('user', None)
    
#     blocks = [
#         {
#             "type": "section",
#             "text": {
#                 "type": "mrkdwn",
#                 "text": "Hello, How can I help you today?"
#             }
#         },
#         {
#             "type": "divider"
#         },
#         {
#             "type": "actions",
#             "elements": [
#                 {
#                     "type": "button",
#                     "text": {
#                         "type": "plain_text",
#                         "text": "Apply leave",
#                         "emoji": True
#                     },
#                     "action_id": "apply_leave",
#                     "style": "primary"  
#                 },
#                 {
#                     "type": "button",
#                     "text": {
#                         "type": "plain_text",
#                         "text": "View leave history",
#                         "emoji": True
#                     },
#                     "action_id": "view_leave_history"
#                 }
#             ]
#         }
#     ]
    
#     # Send the updated home view to Slack
#     response = requests.post(
#         'https://slack.com/api/views.publish',
#         headers={
#             'Authorization': f'Bearer {slack_token}',
#             'Content-Type': 'application/json'
#         },
#         json={
#             'user_id': user_id,
#             'view': {
#                 'type': 'home',
#                 'blocks': blocks
#             }
#         }
#     )
    
#     print(f"Slack API response: {response.status_code}, {response.text}")
#     if response.status_code != 200:
#         return jsonify({"status": "error", "message": response.text}), response.status_code
#     return jsonify({"status": "ok"})

@bp.route('/slack/interactions', methods=['POST'])
def handle_interactions():
    def send_dm_message(user_id, text):
        response = requests.post(
            'https://slack.com/api/conversations.open',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json; charset=utf-8'
            },
            json={
                'users': user_id
            }
        )
        print(user_id)
        if response.status_code != 200:
            return response.text
        channel_id = response.json().get('channel', {}).get('id')
        if not channel_id:
            return "Failed to retrieve DM channel ID."
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json; charset=utf-8'
            },
            json={
                'channel': channel_id,
                'blocks': [
                    {
                        "type": "section",
                        "block_id": "cancel_confirmation",
                        "text": {
                            "type": "mrkdwn",
                            "text": text
                        }
                    }
                ]
            }
        )
        return response.text
    
    def update_pending_leaves(user_id):
        pending_leaves_blocks = view_pending_leaves_ui(user_id)
        blocks = [
            {
                "type": "section",
                "block_id": "pending_leaves_header",
                "text": {
                    "type": "plain_text",
                    "text": "Pending Leaves"
                }
            }
        ]
        blocks.extend(pending_leaves_blocks)
        blocks.append({"type": "divider"})

        # Update the specific blocks in the home UI
        response = requests.post(
            'https://slack.com/api/views.publish',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json'
            },
            json={
                'user_id': user_id,
                'view': {
                    'type': 'home',
                    'blocks': blocks
                }
            }
        )
        return response

    def default_home_ui():
        default_home_ui = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hello, How can I help you today?"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Apply leave",
                            "emoji": True
                        },
                        "action_id": "apply_leave",
                        "style": "primary"  # Green button
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View leave history",
                            "emoji": True
                        },
                        "action_id": "view_leave_history"
                    }
                ]
            }
        ]
        return default_home_ui
    
    def update_home_ui(user_id, slack_token):
        existing_blocks = default_home_ui().copy()
        existing_blocks.append({
            "type": "section",
            "block_id": "pending_leaves_header",
            "text": {
                "type": "plain_text",
                "text": "Pending Leaves"
            }
        })
        pending_leaves_blocks = view_pending_leaves_ui(user_id)
        updated_blocks = existing_blocks + pending_leaves_blocks 
        response = requests.post(
            'https://slack.com/api/views.publish',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json'
            },
            json={
                'user_id': user_id,
                'view': {
                    'type': 'home',
                    'blocks': updated_blocks
                }
            }
        )
        return response

    def get_user_name(user_id):
        response = requests.get(
            'https://slack.com/api/users.info',
            headers={
                'Authorization': f'Bearer {slack_token}'
            },
            params={
                'user': user_id
            }
        )
        user_info = response.json()
        if user_info.get('ok'):
            return user_info.get('user', {}).get('real_name', 'User')
        else:
            return 'User'
        
    if request.content_type != 'application/x-www-form-urlencoded':
        return jsonify({"error": "Unsupported Media Type"}), 415
    payload = request.form.get('payload')
    if not payload:
        return jsonify({"error": "No payload found"}), 400
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON in payload"}), 400

    action_id = data.get('actions', [{}])[0].get('action_id')
    leave_id = data.get('actions', [{}])[0].get('value')
    user_id = data.get('user', {}).get('id')
    print("ACTIONNNS: ",action_id)
    print()
    if data.get('type') == 'view_submission':
        callback_id = data.get('view', {}).get('callback_id')
        values = data.get('view', {}).get('state', {}).get('values', {})
        view_id = data.get('view', {}).get('id')
        if callback_id == 'apply_leave_modal':
            start_date = values.get('start_date', {}).get('start_date', {}).get('selected_date')
            end_date = values.get('end_date', {}).get('end_date', {}).get('selected_date')
            reason = values.get('reason', {}).get('reason', {}).get('value')
            user_name = get_user_name(user_id)
            response_message = apply_leave(user_id, start_date, end_date, reason, user_name)
            print(response_message)
            update_response = update_home_ui(user_id, slack_token)

            if 'error' in dm_response or update_response.status_code != 200:
                return jsonify({"status": "error", "message": "Failed to update the home UI or send DM."}), 500
            return jsonify({"status": "ok"})
            update_modal_view = {
                "type": "modal",
                "callback_id": "apply_leave_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Apply for Leave"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_message
                        }
                    }
                ]
            }

            response = requests.post(
                'https://slack.com/api/views.update',
                headers={
                    'Authorization': f'Bearer {slack_token}',
                    'Content-Type': 'application/json; charset=utf-8'
                },
                json={
                    'view_id': view_id,
                    'view': update_modal_view
                }
            )

            print(f"Slack API response: {response.status_code}, {response.text}")

            if response.status_code != 200:
                return jsonify({"status": "error", "message": response.text}), response.status_code

            return jsonify({"status": "ok"})
    if action_id in ["apporve","decline"]:
        response = handle_interactive_message(data)
        if response.status_code != 200:
                return jsonify({"status": "error", "message": response.text}), response.status_code
        return jsonify({"status": "ok"})
    if action_id == 'apply_leave': 
        trigger_id = data.get('trigger_id')  
        print("Opening leave modal")
        modal_view = {
            "type": "modal",
            "callback_id": "apply_leave_modal",
            "title": {
                "type": "plain_text",
                "text": "Apply for Leave"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "start_date",
                    "label": {
                        "type": "plain_text",
                        "text": "Start Date"
                    },
                    "element": {
                        "type": "datepicker",
                        "action_id": "start_date"
                    },
                    "optional": False
                },
                {
                    "type": "input",
                    "block_id": "end_date",
                    "label": {
                        "type": "plain_text",
                        "text": "End Date"
                    },
                    "element": {
                        "type": "datepicker",
                        "action_id": "end_date"
                    },
                    "optional": False
                },
                {
                    "type": "input",
                    "block_id": "reason",
                    "label": {
                        "type": "plain_text",
                        "text": "Reason for Leave"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "reason"
                    },
                    "optional": False
                }
            ],
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            }
        }
        response = requests.post(
            'https://slack.com/api/views.open',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json; charset=utf-8'
            },
            json={
                'trigger_id': trigger_id,
                'view': modal_view
            }
        )
        callback_id = data.get('view', {}).get('callback_id')
        user_id = data.get('user', {}).get('id')
        values = data.get('view', {}).get('state', {}).get('values', {})
        print("CALLBACK ", callback_id)
        print(f"Slack API response: {response.status_code}, {response.text}")
        return jsonify({"status": "ok"})
    if action_id == "view_leave_history":
        trigger_id = data.get('trigger_id')
        user_id = data.get('user', {}).get('id')  
        print("Opening leave history modal")
        leave_balance_message = view_leave_balance(user_id)
        leave_history = view_past_leaves(user_id)
        leave_entries = leave_history.split('\n')
        blocks = [
            {
                "type": "section",
                "block_id": "leave_balance",
                "text": {
                    "type": "mrkdwn",
                    "text": leave_balance_message
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "block_id": "leave_history_header",
                "text": {
                    "type": "plain_text",
                    "text": "Here is your leave history:"
                }
            }
        ]
        for idx, entry in enumerate(leave_entries):
            blocks.append({
                "type": "section",
                "block_id": f"leave_entry_{idx}",
                "text": {
                    "type": "mrkdwn",
                    "text": entry
                }
            })
        modal_view = {
            "type": "modal",
            "callback_id": "leave_history_modal",
            "title": {
                "type": "plain_text",
                "text": "Leave History"
            },
            "blocks": blocks
        }
        response = requests.post(
            'https://slack.com/api/views.open',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json; charset=utf-8'
            },
            json={
                'trigger_id': trigger_id,
                'view': modal_view
            }
        )
        print(f"Slack API response: {response.status_code}, {response.text}")
        if response.status_code != 200:
            return jsonify({"status": "error", "message": response.text}), response.status_code
        return jsonify({"status": "ok"})
    if action_id.startswith('cancel_'):
        leave_id = int(action_id.split('_')[1])
        result = cancel_leave_request(user_id, leave_id)
        update_response = update_home_ui(user_id, slack_token)
        response_message = f"Leave request (ID: {leave_id}) cancelled successfully. Leave days added back to your balance."
        dm_response = send_dm_message(user_id, response_message)
        
        if 'error' in dm_response or update_response.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to update the home UI or send DM."}), 500
        
        return jsonify({"status": "ok", "message": response_message})

# @bp.route('/slack/interactions', methods=['POST'])
# def handle_interactions():
#     if request.content_type != 'application/x-www-form-urlencoded':
#         return jsonify(error="Unsupported Media Type"), 415
#     payload = request.form.get('payload')
#     if not payload:
#         return jsonify(error="No payload found"), 400
#     try:
#         data = json.loads(payload)
#     except json.JSONDecodeError:
#         return jsonify(error="Invalid JSON in payload"), 400
#     action_id = data.get('actions', [{}])[0].get('action_id')
#     user_id = data.get('user', {}).get('id')
#     print("ACTIONNNN: ",action_id)
#     if action_id == 'apply_leave':
#         blocks = [
#             {
#                 "type": "section",
#                 "text": {
#                     "type": "mrkdwn",
#                     "text": "Please fill out the leave application form."
#                 }
#             },
#             {
#                 "type": "input",
#                 "block_id": "start_date",
#                 "element": {
#                     "type": "datepicker",
#                     "placeholder": {
#                         "type": "plain_text",
#                         "text": "Select a start date"
#                     },
#                     "action_id": "start_date"
#                 },
#                 "label": {
#                     "type": "plain_text",
#                     "text": "Start Date"
#                 }
#             },
#             {
#                 "type": "input",
#                 "block_id": "end_date",
#                 "element": {
#                     "type": "datepicker",
#                     "placeholder": {
#                         "type": "plain_text",
#                         "text": "Select an end date"
#                     },
#                     "action_id": "end_date"
#                 },
#                 "label": {
#                     "type": "plain_text",
#                     "text": "End Date"
#                 }
#             },
#             {
#                 "type": "input",
#                 "block_id": "reason",
#                 "element": {
#                     "type": "plain_text_input",
#                     "multiline": True,
#                     "action_id": "reason"
#                 },
#                 "label": {
#                     "type": "plain_text",
#                     "text": "Reason for leave"
#                 }
#             },
#             {
#                 "type": "actions",
#                 "elements": [
#                     {
#                         "type": "button",
#                         "text": {
#                             "type": "plain_text",
#                             "text": "Submit",
#                             "emoji": True
#                         },
#                         "style": "primary",
#                         "action_id": "submit_leave"
#                     }
#                 ]
#             }
#         ]
#         response = {
#             "response_type": "ephemeral",
#             "blocks": blocks
#         }

#         return jsonify(response)

#     elif action_id == 'view_leave_history':
#         # Respond with leave history
#         leave_history_blocks = [
#             {
#                 "type": "section",
#                 "text": {
#                     "type": "mrkdwn",
#                     "text": "Here is your leave history:"
#                 }
#             }
#             # Add more blocks here for displaying leave history
#         ]

#         response = {
#             "response_type": "ephemeral",
#             "blocks": leave_history_blocks
#         }

#         return jsonify(response)

#     return jsonify({"status": "error", "message": "Unknown action"}), 400

# @bp.route('/slack/interactions', methods=['POST'])
# def handle_interactions():
#     print("HIII")
#     print(request.content_type)
#     if request.content_type != 'application/x-www-form-urlencoded':
#         return jsonify(error="Unsupported Media Type"), 415
#     payload = request.form.get('payload')
    
#     if not payload:
#         return jsonify(error="No payload found"), 400

#     try:
#         # Parse the payload JSON string
#         data = json.loads(payload)
#     except json.JSONDecodeError:
#         return jsonify(error="Invalid JSON in payload"), 400

#     action_id = data.get('actions', [{}])[0].get('action_id')
#     leave_id = data.get('actions', [{}])[0].get('value')
#     user_id = data.get('user', {}).get('id')

#     print(f"Action ID: {action_id}, Leave ID: {leave_id}, User ID: {user_id}")

#     response = handle_interactive_message(data)
#     # if action_id == 'approve':
#     #     response = approve_or_decline_leave(user_id, int(leave_id), 'approve')
#     # elif action_id == 'decline':
#     #     response = approve_or_decline_leave(user_id, int(leave_id), 'decline')
#     # else:
#     #     response = "Unknown action."
    
#     return jsonify(response_type='ephemeral', text=response)

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