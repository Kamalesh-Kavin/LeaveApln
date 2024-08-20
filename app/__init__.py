from flask import Flask
from .models import db, User, assign_color_to_user, generate_unique_color
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from urllib3.util import ssl_
import certifi
import ssl
from datetime import datetime

load_dotenv(dotenv_path='../.env') 


slack_token = os.getenv("SLACK_BOT_TOKEN")
slack_token = 'xoxb-7584405679664-7561620439074-XBJ88tjnGJyCGHWUZ39VIIU9'

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Initialize the Slack client with the custom SSL context
client = WebClient(token=slack_token, ssl=ssl_context)

print("In init.py")
def assign_colors_to_existing_users():
    """Assigns unique colors to existing users without colors."""
    users = User.query.filter(User.color.is_(None)).all()
    existing_colors = set(user.color for user in User.query.filter(User.color.isnot(None)).all())

    for user in users:
        user.color = generate_unique_color(existing_colors)
        existing_colors.add(user.color)
        db.session.commit()

    print("Assigned unique colors to existing users.")

def assign_colors_to_existing_users():
    """Assigns unique colors to existing users without colors."""
    users = User.query.filter(User.color.is_(None)).all()
    existing_colors = set(user.color for user in User.query.filter(User.color.isnot(None)).all())

    for user in users:
        user.color = generate_unique_color(existing_colors)
        existing_colors.add(user.color)
        db.session.commit()

    print("Assigned unique colors to existing users.")

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
                    new_user = User(slack_id=user_id, name=user_name, is_admin=True, role="Manager", leave_balance=14)
                    db.session.add(new_user)
                    assign_color_to_user(new_user)
                    db.session.commit()
                    return f"{user_name} has been added and set as the default admin."
            else:
                return "No primary owner found."
        else:
            return "Failed to retrieve user list from Slack."
    except SlackApiError as e:
        return f"Slack API error: {str(e)}"

def update_manager_leave_balances():
    current_year = datetime.now().strftime('%Y')

    managers = User.query.filter_by(role="Manager").all()
    for manager in managers:
        print("CHECKKKKK: ",manager.last_reset_month,current_year)
        last_reset_year = manager.last_reset_month.split('-')[0]
        if last_reset_year != current_year:  # Check if the balance needs to be updated
            # Update balance to 14 + any remaining balance from the previous year
            manager.leave_balance = 14 + manager.leave_balance
            manager.last_reset_month = current_year  # Update the last reset year
            db.session.commit()

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
            update_manager_leave_balances()
            print("Manager leave balances updated.")
        except Exception as e:
            print(f"Error creating database tables: {e}")
        assign_colors_to_existing_users()

    from . import routes
    app.register_blueprint(routes.bp)
    return app
