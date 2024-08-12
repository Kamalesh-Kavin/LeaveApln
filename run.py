from app import create_app
from flask_migrate import Migrate

print("Creating Flask app...")
app = create_app()
migrate = Migrate(app, db)
print("Flask app created successfully.")

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(debug=True)