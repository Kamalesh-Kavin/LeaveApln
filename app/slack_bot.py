from slack_sdk import WebClient
import os
import certifi
import requests

slack_token = os.getenv("SLACK_BOT_TOKEN")
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
    response = requests.post(url, headers=headers, json=payload, verify=certifi.where())
    if response.status_code != 200:
        raise Exception(f"Error sending message: {response.text}")
    print(response)
    return response
