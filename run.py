from app import create_app

print("Creating Flask app...")
app = create_app()
print("Flask app created successfully.")

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(debug=True)