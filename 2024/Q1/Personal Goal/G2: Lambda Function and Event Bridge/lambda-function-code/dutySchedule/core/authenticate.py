import requests
import json
import os

class UserAuthenticate:

    def __init__(self, *args, **kwargs):
        self.base_url = os.environ['BASE_API_URL']
        self.email = os.environ['USER_EMAIL']
        self.password = os.environ['USER_PASSWORD']
        self.authentication_token = None

    def authenticate(self):
        payload = {
            'email': self.email,
            'password': self.password
        }
        headers = {
            "Content-Type": "application/json"
        }
        login_url = f"{self.base_url}/api/v1/auth/"
        response = requests.post(login_url, headers=headers, data=json.dumps(payload))
        if response.status_code == 201:
            data = json.loads(response.text)
            self.authentication_token = data.get('jwt')
        return self.authentication_token
