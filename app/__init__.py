from flask import Flask
from .models import db, User
from .manager import create_manager
import os
from dotenv import load_dotenv

# Load the .env file
load_dotenv(dotenv_path='../.env') 

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully.")
            slack_id = 'U07GHFFEHDH' 
            name = "testM"
            result = create_manager(slack_id, name)
            print(result)
        except Exception as e:
            print(f"Error creating database tables: {e}")

    from . import routes
    app.register_blueprint(routes.bp)

    return app
