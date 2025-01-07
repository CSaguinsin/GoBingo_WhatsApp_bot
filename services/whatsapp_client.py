import requests
import os


class WhatsAppClient:
    def __init__(self, api_url, token):
        self.api_url = api_url
        self.token = token

    def download_media(self, media_url):
        response = requests.get(media_url)
        if response.status_code == 200:
            return response.content
        return None

    def send_message(self, chat_id, message):
        payload = {'chat_id': chat_id, 'text': message}
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        response = requests.post(f"{self.api_url}/send", json=payload, headers=headers)
        return response.status_code == 200

whapi_client = WhatsAppClient(api_url=os.getenv('API_URL'), token=os.getenv('TOKEN'))
