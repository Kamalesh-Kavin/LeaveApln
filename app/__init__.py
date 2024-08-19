from flask import Flask
from .models import db, User
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv(dotenv_path='../.env') 

slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_token = 'xoxb-7584405679664-7561620439074-XN60Lx3w8QAYhSCm42VI0bFP'
client = WebClient(token=slack_token)
print("In init.py")
def get_workspace_owner():
    try:
        response = client.users_list()
        if response.get("ok"):
            members = response.get("members", [])
            primary_owner = next((user for user in members if user.get('is_primary_owner')), None)
            
            if primary_owner:
                user_id = primary_owner['id']
                user_name = primary_owner['real_name']
                user = User.query.filter_by(slack_id=user_id).first()
                if user:
                    user.is_admin = True
                    db.session.commit()
                    return f"{user_name} has been set as the default admin."
                else:
                    new_user = User(slack_id=user_id, name=user_name, is_admin=True,role="Manager")
                    db.session.add(new_user)
                    db.session.commit()
                    return f"{user_name} has been added and set as the default admin."
            else:
                return "No primary owner found."
        else:
            return "Failed to retrieve user list from Slack."
    except SlackApiError as e:
        return f"Slack API error: {str(e)}"

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully.")
            result = get_workspace_owner()
            print("Result of workspace owner func: ",result)

            # slack_id = 'U07GHFFEHDH' 
            # name = "testM"
            # result = create_manager(slack_id, name)
            # print(result)
        except Exception as e:
            print(f"Error creating database tables: {e}")

    from . import routes
    app.register_blueprint(routes.bp)

    return app
