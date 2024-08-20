from flask import Flask
from .models import db, User
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import certifi
import ssl
from datetime import datetime
import os
from .logger import log
from .color_manager import assign_colors_to_existing_users
from .slack_manager import get_workspace_owner
from .user_manager import update_manager_leave_balances

def load_env(file_path):
    with open(file_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

load_env('.env')
slack_token = os.getenv("SLACK_BOT_TOKEN")
log.info("Slack Token in Init: %s", slack_token)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Initialize the Slack client with the custom SSL context
client = WebClient(token=slack_token, ssl=ssl_context)

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            log.info("Database tables created successfully.")
            result = get_workspace_owner(client)
            log.info("Result of workspace owner func: %s",result)
            update_manager_leave_balances()
            log.info("Manager leave balances updated.")
        except Exception as e:
            log.error(f"Error creating database tables: {e}")
        assign_colors_to_existing_users()

    from . import routes
    app.register_blueprint(routes.bp)
    return app
