from flask import Flask
from dotenv import load_dotenv
from controller.webhook_controller import webhook_blueprint
from controller.message_controller import messages_blueprint
from controller.webhook_controller import webhook_blueprint
from controller.message_controller import messages_blueprint, MessageController
from model.document_processor import DocumentProcessor
from view.message_view import MessageView
from services.whatsapp_client import WhatsAppClient
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
    app.register_blueprint(webhook_blueprint)  # Existing webhook blueprint
    
        # Instantiate MessageController and register routes
    document_processor = DocumentProcessor()
    whapi_client = WhatsAppClient(api_url=os.getenv('API_URL'), token=os.getenv('TOKEN')) 
    user_state = ...          # Replace with your actual implementation
    message_view = MessageView()
    message_controller = MessageController(document_processor, whapi_client, user_state, message_view)

    app.register_blueprint(messages_blueprint, url_prefix='')

    
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

    # Get the PORT from the environment variable and strip any comments
    port_env = os.getenv('PORT', '80').split('#')[0].strip()  # Remove comments after '#'
    try:
        port = int(port_env)  # Convert to integer
    except ValueError:
        logging.error(f"Invalid PORT value: '{port_env}'. Falling back to default port 80.")
        port = 80  # Default to port 80 if invalid

    # Log the startup information
    logging.info(f"Starting bot server on port {port}")
    logging.info(f"Webhook URL: {os.getenv('BOT_URL')}")

    app.run(host='0.0.0.0', port=port, debug=True)

