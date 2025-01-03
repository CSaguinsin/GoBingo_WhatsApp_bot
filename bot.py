from flask import Flask
from dotenv import load_dotenv
from controller.webhook_controller import webhook_blueprint
import os

def create_app():
    load_dotenv()
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(webhook_blueprint)
    
    @app.route('/', methods=['GET'])
    def index():
        return 'Document Processing Bot is running'
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 80))
    app.run(host='0.0.0.0', port=port, debug=True)