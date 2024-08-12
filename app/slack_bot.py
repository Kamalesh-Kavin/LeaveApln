from slack_sdk import WebClient
import os

slack_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_token)

def send_message(channel_id, text):
    response = client.chat_postMessage(
        channel=channel_id,
        text=text
    )
    print(response)
    return response
