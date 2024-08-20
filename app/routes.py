from flask import Blueprint, request, jsonify, render_template
from .intern import apply_leave, cancel_leave_request, view_past_leaves, view_leave_balance, view_pending_leaves, view_pending_leaves_ui
from .manager import approve_or_decline_leave, view_intern_leave_history, view_all_pending_leaves, view_all_pending_leaves_ui, format_intern_users_for_modal, handle_interactive_message, make_manager
from .models import User,db, ManagerMapping, LeaveRequest, assign_color_to_user, LeaveStatus
from .slack_bot import update_message
import json
import requests
import os
from datetime import timedelta

bp = Blueprint('routes', __name__)
slack_token = 'xoxb-7584405679664-7561620439074-XBJ88tjnGJyCGHWUZ39VIIU9'
print("SLACKKK",slack_token)

def get_slack_user_info(user_id):
    url = f"https://slack.com/api/users.info"
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'user': user_id
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if data.get('ok'):
        return data.get('user', {})
    else:
        return None
    
@bp.route('/')
def home():
    return "Welcome to the Leave Bot Application!!"

@bp.route('/calendar')
def calendar():
    return render_template('calendar.html')

@bp.route('/api/leave-events', methods=['GET'])
def get_leave_events():
    leave_requests = LeaveRequest.query.filter_by(status=LeaveStatus.APPROVED).all()
    events = []
    for request in leave_requests:
        events.append({
            'id': request.id,
            'title': f"{request.user.name} - {request.reason}",
            'start': request.start_date.isoformat(),
            'end': (request.end_date + timedelta(days=1)).isoformat(),  # FullCalendar expects end date to be exclusive
            'backgroundColor': request.user.color  # Color assigned to user
        })
    return jsonify(events)

@bp.route('/slack/apps_home', methods=['POST'])
def app_home():
    # # to enable link
    # if request.json.get('type') == 'url_verification':
    #     return jsonify(challenge=request.json.get('challenge'))

    print("HOME UI Loading...")
    data = request.json
    print("DATA: ",data)

    user_id = data.get('event', {}).get('user') or data.get('event', {}).get('message', {}).get('user') or data.get('event', {}).get('edited', {}).get('user')
    print("\nUser id: ",user_id)
    if not user_id:
        return jsonify({"status": "error", "message": "User ID not found"}), 400
    
    user = User.query.filter_by(slack_id=user_id).first()
    print("User: ",user)
    
    if not user:
        slack_user_info = get_slack_user_info(user_id)
        print("Slack user info",get_slack_user_info)
        user_name = slack_user_info.get('profile', {}).get('real_name', 'Unknown')
        user = User(slack_id=user_id, name=user_name)
        db.session.add(user)
        assign_color_to_user(user)
        db.session.commit()

    is_intern = user.role == 'Intern'
    is_manager = user.role == 'Manager'
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
        }
    ]

    if is_intern:
        blocks.append({
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
                    "style": "primary"
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
        })
        pending_leaves_blocks = view_pending_leaves_ui(user_id)
        if pending_leaves_blocks:
            blocks.append({
                "type": "section",
                "block_id": "pending_leaves_header",
                "text": {
                    "type": "plain_text",
                    "text": "Pending Leaves"
                }
            })
            blocks.extend(pending_leaves_blocks)

    elif is_manager:
        blocks.append({
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
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Users",
                        "emoji": True
                    },
                    "action_id": "view_users",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View User Leave History",
                        "emoji": True
                    },
                    "action_id": "view_user_leave_history"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View calendar",
                        "emoji": True
                    },
                    "action_id": "view_calendar"
                },
            ]
        })
        pending_leaves = view_all_pending_leaves_ui(user_id)
        if pending_leaves:
            blocks.append({
                "type": "section",
                "block_id": "pending_leaves_header",
                "text": {
                    "type": "plain_text",
                    "text": "Pending Leave Requests"
                }
            })
            blocks.extend(pending_leaves)
        manager_pending_leaves = view_pending_leaves_ui(user_id)
        if manager_pending_leaves:
            blocks.append({
                "type": "section",
                "block_id": "manager_pending_leaves_header",
                "text": {
                    "type": "plain_text",
                    "text": "Your Pending Leaves"
                }
            })
            blocks.extend(manager_pending_leaves)
    
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
                        "style": "primary"  
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
    
    def default_home_manager_ui():
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
        }
        ]
        blocks.append({
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
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Users",
                        "emoji": True
                    },
                    "action_id": "view_users",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View User Leave History",
                        "emoji": True
                    },
                    "action_id": "view_user_leave_history"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View calendar",
                        "emoji": True
                    },
                    "action_id": "view_calendar"
                },
            ]
        })
        return blocks
    
    def update_home_manager_ui(user_id, slack_token):
        existing_blocks = default_home_manager_ui().copy()
        existing_blocks.append({
            "type": "section",
            "block_id": "pending_leaves_header",
            "text": {
                "type": "plain_text",
                "text": "Pending Leave Requests"
            }
        })
        pending_leaves_blocks = view_all_pending_leaves_ui(user_id)
        existing_blocks = existing_blocks + pending_leaves_blocks
        existing_blocks.append({
            "type": "section",
            "block_id": "manager_pending_leaves_header",
            "text": {
                "type": "plain_text",
                "text": "Your Pending Leaves"
            }
        })

        manager_pending_leaves = view_pending_leaves_ui(user_id)
        updated_blocks = existing_blocks + manager_pending_leaves
        print("\n Updated blocks: \n",updated_blocks)
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

    def open_intern_users_modal(trigger_id, slack_id):
        manager = User.query.filter_by(slack_id=slack_id).first()
        if not manager:
            return "Manager not found."
        intern_users = [mapping.employee for mapping in manager.managed_employees]
        if not intern_users:
            return "No intern users found for this manager."
        blocks = format_intern_users_for_modal(intern_users)
        
        response = requests.post('https://slack.com/api/views.open', headers={
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }, json={
            "trigger_id": trigger_id,
            "view": {
                "type": "modal",
                "callback_id": "intern_users_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Intern Users"
                },
                "blocks": blocks
            }
        })
        
        # Check if the request was successful
        if response.status_code == 200 and response.json().get('ok'):
            return "ok"
        else:
            return "no"

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
    print("ACTIONSSSS:",action_id)
    leave_id = data.get('actions', [{}])[0].get('value')
    user_id = data.get('user', {}).get('id')
    if data.get('type') == 'view_submission':
        callback_id = data.get('view', {}).get('callback_id')
        values = data.get('view', {}).get('state', {}).get('values', {})
        view_id = data.get('view', {}).get('id')
        if callback_id == 'apply_leave_modal':
            start_date = values.get('start_date', {}).get('start_date', {}).get('selected_date')
            end_date = values.get('end_date', {}).get('end_date', {}).get('selected_date')
            print("STARTTT",start_date,end_date)
            reason = values.get('reason', {}).get('reason', {}).get('value')
            user_name = get_user_name(user_id)
            response_message = apply_leave(user_id, start_date, end_date, reason, user_name)
            print(response_message)
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
        if callback_id == 'intern_leave_history_request':
            print("Data: ",data)
            slack_id = values.get('slack_id_block', {}).get('slack_id_input', {}).get('value')
            print("SLACK_ID",slack_id)
            user = User.query.filter_by(slack_id=slack_id).first()
            if not user:
                return "User not found."
            manager_mapping = ManagerMapping.query.filter_by(employee_id=slack_id).first()
            if not manager_mapping:
                return "No manager assigned to this user."
            manager = User.query.filter_by(slack_id=manager_mapping.manager_id).first()
            if not manager:
                return "Manager not found."
            leave_history = view_intern_leave_history(slack_id,manager.slack_id)
            leave_history_message = f"Leave History for {user.name}:\n\n" + leave_history

            # Update the modal with the leave history
            update_modal_view = {
                "type": "modal",
                "callback_id": "intern_leave_history_request",
                "title": {
                    "type": "plain_text",
                    "text": "Leave History"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": leave_history_message
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
    if action_id == 'view_calendar':
        response = requests.post(
            'https://slack.com/api/views.open',
            headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json'
            },
            json={
                "trigger_id": data['trigger_id'],
                "view": {
                    "type": "modal",
                    "callback_id": "calendar_modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Leave Calendar"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "block_id": "calendar_block",
                            "text": {
                                "type": "mrkdwn",
                                "text": "Here is the leave calendar:"
                            },
                            "accessory": {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Open Calendar",
                                    "emoji": True
                                },
                                "action_id": "open_calendar",
                                "url": f"{'https://46b1-14-99-67-22.ngrok-free.app'}/calendar"
                            }
                        }
                    ]
                }
            }
        )
        if response.status_code != 200:
            print(f"Error opening modal: {response.text}")
        return jsonify({"status": "ok"})

    if action_id == 'view_user_leave_history':
        trigger_id = data.get('trigger_id')
        print("TRI",trigger_id)
        modal_view = {
            "type": "modal",
            "callback_id": "intern_leave_history_request",
            "title": {
                "type": "plain_text",
                "text": "Leave History"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "slack_id_block",
                    "label": {
                        "type": "plain_text",
                        "text": "Enter User ID"
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "slack_id_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., U07GHFFEHDH"
                        }
                    },
                    "optional": False  
                }
            ],
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            }
        }
        response = requests.post('https://slack.com/api/views.open', headers={
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }, json={
            "trigger_id": trigger_id,
            "view": modal_view
        })
        callback_id = data.get('view', {}).get('callback_id')
        user_id = data.get('user', {}).get('id')
        print("CALLBACK ", callback_id)
        print(f"Slack API response: {response.status_code}, {response.text}")
        return jsonify({"status": "ok"})
    if action_id == "view_users":
        trigger_id = data.get('trigger_id')
        print("Trigger: ", trigger_id)
        response = open_intern_users_modal(trigger_id, user_id)
        print("RESPONSE: ", response)
        if response == "ok":
            return jsonify({"status": "ok"})
        else:
            error_message = response
            error_response = requests.post('https://slack.com/api/views.open', headers={
                'Authorization': f'Bearer {slack_token}',
                'Content-Type': 'application/json'
            }, json={
                "trigger_id": trigger_id,
                "view": {
                    "type": "modal",
                    "callback_id": "error_modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Error"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "block_id": "error_message",
                            "text": {
                                "type": "plain_text",
                                "text": error_message
                            }
                        }
                    ]
                }
            })
            
            if error_response.status_code == 200 and error_response.json().get('ok'):
                return jsonify({"status": "error", "message": error_message})
            else:
                return jsonify({"status": "error", "message": "Failed to display error message"}), 500

    if action_id in ["approve","decline"]:
        print("INside aprove")
        response = handle_interactive_message(data)
        print("HII")
        update_response = update_home_manager_ui(user_id, slack_token)
        print("RESSponse",response)
        if "error" in response or update_response.status_code != 200:
                return jsonify({"status": "error", "message": "Failed to update the home UI or send DM."}), 500
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
        user = User.query.filter_by(slack_id=user_id).first()
        print("USERRR: ",user)
        print("user role:",user.role)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        if user.role == 'Manager':
            update_response = update_home_manager_ui(user_id, slack_token)
        else:
            update_response = update_home_ui(user_id, slack_token)
        response_message = f"Leave request (ID: {leave_id}) cancelled successfully. Leave days added back to your balance."
        dm_response = send_dm_message(user_id, response_message)
        
        if 'error' in dm_response or update_response.status_code != 200:
            return jsonify({"status": "error", "message": "Failed to update the home UI or send DM."}), 500
        
        return jsonify({"status": "ok", "message": response_message})

@bp.route('/slack/admin',methods=['POST'])
def admin_stuffs():
    def make_admin(user_id):
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return f"User with ID {user_id} not found."
            user.is_admin = True
            db.session.commit()
            return f"User {user.name} (ID: {user.id}) has been promoted to Admin."
        except Exception as e:
            db.session.rollback()
            return f"An error occurred while promoting user: {e}"

    def is_admin(user_id):
        user = User.query.filter_by(slack_id=user_id).first()
        return user.is_admin if user else False

    data = request.form
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    command = data.get('command')
    text = data.get('text', '').strip()

    if not is_admin(user_id):
        return "Access denied. Only admins can use this command."
    
    if command == '/viewmanagers':
        managers = User.query.filter_by(role='Manager').with_entities(User.slack_id, User.name).all()
        print("MAN", managers)
        manager_list = [f"Slack ID: {manager.slack_id} - Name: {manager.name}" for manager in managers]
        return "\n".join(manager_list)
    
    elif command == '/assignmanager':
        try:
            texts=text.split()
            if len(texts) != 2:
                return "Invalid format. Please use the format: /command intern_id manager_id"
            intern_id=texts[0]
            manager_id=texts[1]
            intern = User.query.filter_by(slack_id=intern_id).first()
            manager = User.query.filter_by(slack_id=manager_id).first()
            if not intern:
                return f"Intern with ID {intern_id} not found."
            if not manager:
                return f"Manager with ID {manager_id} not found."
            if manager.role != 'Manager':
                return f"User with ID {manager_id} is not a manager."
            existing_mapping = ManagerMapping.query.filter_by(employee_id=intern_id).first()
            if existing_mapping:
                db.session.delete(existing_mapping)
            new_mapping = ManagerMapping(employee_id=intern_id, manager_id=manager_id)
            db.session.add(new_mapping)
            db.session.commit()
            return f"Manager {manager.name} (ID: {manager.slack_id}) successfully assigned to {intern.name} (ID: {intern.slack_id})."

        except Exception as e:
            db.session.rollback() 
            return f"An error occurred while assigning manager: {e}"
        
    elif command == '/makemanager':
        try:
            intern_id = text
            return make_manager(intern_id)
        except ValueError:
            return "Please provide a valid intern ID."
    
    elif command == '/makeadmin':
        try:
            user_to_promote_id = int(text)
            return make_admin(user_to_promote_id)
        except ValueError:
            return "Please provide a valid user ID."
        
    elif command == '/viewadmins':
        admins = User.query.filter_by(is_admin=True).with_entities(User.slack_id, User.name, User.role).all()
        if not admins:
            return "No admins found."
        admin_list = [f"Slack ID: {admin[0]} - Name: {admin[1]} - Role: {admin[2]}" for admin in admins]
        return "\n".join(admin_list)

    elif command == '/viewallusers':
        users = db.session.query(
            User.slack_id,
            User.name,
            User.role,
            ManagerMapping.manager_id
        ).outerjoin(
            ManagerMapping, User.slack_id == ManagerMapping.employee_id
        ).with_entities(
            User.slack_id,
            User.name,
            User.role,
            ManagerMapping.manager_id
        ).all()
        if not users:
            return "No users found."
        user_list = [
            f"Slack ID: {user[0]} - Name: {user[1]} - Role: {user[2]} - Manager ID: {user[3] or 'None'}"
            for user in users
        ]
        return "\n".join(user_list)
    
    else:
        response = "Unknown command."

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
    
    elif command == "/calendar":
        # Respond with a message
        response =  "You can view the leave calendar here: https://46b1-14-99-67-22.ngrok-free.app/calendar"
    
        # return jsonify(response_message)
    
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
            leave_request = LeaveRequest.query.filter_by(id=leave_id).one()
            channel_id = leave_request.channel_id
            message_ts = leave_request.message_ts
            updated_text = f"Leave request {leave_id} has been {action}d by <@{user_id}>."
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
                        "text": f"*Status:* {'Approved' if action == 'approve' else 'Declined'}"
                    }
                }
            ]
            update_message(channel_id, message_ts, updated_text, updated_blocks)
        except ValueError:
            response = "Please provide a valid leave ID."

    elif command == '/leavehistory':
        intern_id = text.strip()
        manager_mapping = ManagerMapping.query.filter_by(employee_id=intern_id).first()
        if not manager_mapping:
            response="Manager not found"
        else:
            response = view_intern_leave_history(intern_id,manager_mapping.manager_id)

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