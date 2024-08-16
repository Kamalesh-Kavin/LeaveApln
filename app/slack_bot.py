from slack_sdk import WebClient
import certifi
import requests
import os
import json
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from .models import LeaveRequest,db

load_dotenv(dotenv_path='../.env')
slack_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_token)

def update_message_for_manager(channel_id, message_ts, user_name):
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    headers = {
        'Authorization': f'Bearer {slack_token}',
        'Content-Type': 'application/json'
    }
    
    updated_message = {
        "channel": channel_id,
        "ts": message_ts,
        "text": f"This leave request was cancelled by {user_name}.",
        "attachments": [
            {
                "fallback": "Leave request update",
                "color": "#ff0000",
                "title": "Leave Request Update",
                "text": f"This leave request was cancelled by {user_name}."
            }
        ]
    }

    response = requests.post('https://slack.com/api/chat.update', headers=headers, json=updated_message)
    
    if not response.ok:
        raise Exception(f"Failed to update message: {response.text}")

    return response

def update_message(channel_id, message_ts, updated_text, updated_blocks):
    try:
        url = "https://slack.com/api/chat.update"
        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "channel": channel_id,
            "ts": message_ts,
            "text": updated_text,
            "blocks": updated_blocks
        }
        response = requests.post(url, headers=headers, json=payload, verify=certifi.where())
        if not response.ok or not response.json().get('ok', False):
            raise Exception(f"Slack API Error: {response.json().get('error')}")

        print(f"Message updated successfully: {response.text}")
        return response.text

    except Exception as e:
        print(f"Error updating message: {e}")
        raise

def send_message_to_manager(slack_id, leave_id, message):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": slack_id,
        "text": message,
        "blocks": [
            {
                "type": "section",
                "block_id": "section-identifier",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "actions",
                "block_id": "actions-identifier",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve",
                            "emoji": True
                        },
                        "action_id": "approve",
                        "value": str(leave_id) 
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Decline",
                            "emoji": True
                        },
                        "action_id": "decline",
                        "value": str(leave_id) 
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), verify=certifi.where())
        response.raise_for_status()
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise Exception(f"Slack API Error: {response_data.get('error')}")
        
        channel_id = response_data.get('channel')
        message_ts = response_data.get('ts')
        print(f"Message sent to manager successfully: {response_data}")
        leave_request = LeaveRequest.query.get(leave_id)
        if leave_request:
            leave_request.channel_id = channel_id
            leave_request.message_ts = message_ts
            db.session.commit()
        return response_data

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise

    except Exception as e:
        print(f"Error sending message: {e}")
        raise

def send_message_from_manager(slack_id, message):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": slack_id,
        "text": message
    }
    try:
        response = requests.post(url, headers=headers, json=payload, verify=certifi.where())
        response.raise_for_status()
        response_data = response.json()
        
        if not response_data.get("ok"):
            raise Exception(f"Slack API Error: {response_data.get('error')}")
        
        print(f"Message sent successfully: {response_data}")
        return response_data

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise

    except Exception as e:
        print(f"Error sending message: {e}")
        raise
