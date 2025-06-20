from app import app, init_app

if __name__ == '__main__':
    with app.app_context():
        init_app()
        print("Database initialized successfully!") 