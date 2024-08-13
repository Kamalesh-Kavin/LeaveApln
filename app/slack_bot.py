from slack_sdk import WebClient
import certifi
import requests
import os

slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_token="xoxb-7584405679664-7561620439074-sJ8NoZP9xBi79h2eYEEc4gYb"
client = WebClient(token=slack_token)

def send_message(slack_id, message):
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
