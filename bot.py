from flask import Flask
from dotenv import load_dotenv
from controller.webhook_controller import webhook_blueprint
import os
import requests
import logging

def setup_webhook(api_url, bot_url, token):
    """Setup webhook for the bot"""
    try:
        settings = {
            'webhooks': [{
                'url': bot_url,
                'events': [{'type': "messages", 'method': "post"}],
                'mode': "method"
            }]
        }
        
        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json'
        }
        
        response = requests.patch(
            f"{api_url}/settings",
            json=settings,
            headers=headers
        )
        
        if response.status_code == 200:
            logging.info(f"Webhook set up successfully at {bot_url}")
        else:
            logging.error(f"Failed to set up webhook: {response.text}")
            
    except Exception as e:
        logging.error(f"Error setting up webhook: {str(e)}")

def create_app():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(webhook_blueprint)
    
    # Setup webhook route
    @app.route('/', methods=['GET'])
    def index():
        return 'Document Processing Bot is running'
    
    # Setup webhook with current URL
    bot_url = os.getenv('BOT_URL')
    api_url = os.getenv('API_URL')
    token = os.getenv('TOKEN')
    
    if bot_url and api_url and token:
        setup_webhook(api_url, bot_url, token)
    else:
        logging.error("Missing required environment variables (BOT_URL, API_URL, or TOKEN)")
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 80))
    
    # Log the startup information
    logging.info(f"Starting bot server on port {port}")
    logging.info(f"Webhook URL: {os.getenv('BOT_URL')}")
    
    app.run(host='0.0.0.0', port=port, debug=True)