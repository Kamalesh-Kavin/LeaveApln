from slack_sdk import WebClient
import certifi
import requests
import os
import json

slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_token="xoxb-7584405679664-7561620439074-SeSX666k57aTi8BXnCP6kFcW"
client = WebClient(token=slack_token)


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
                        "value": str(leave_id)  # Use leave_id as value
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Decline",
                            "emoji": True
                        },
                        "action_id": "decline",
                        "value": str(leave_id)  # Use leave_id as value
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
        
        print(f"Message sent to manager successfully: {response_data}")
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
