import requests
import json
import os
from typing import Dict, List


class UserService:
    """
    Class for getting the user's tokens'
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the UserService instance.
        Returns:
           lists of users with id, token, and user_id
            id (number): token id
            token (string): token string
            user_id (number): user id
          """
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
        return self

    def get_fcm_tokens(self):
        users = []
        if not self.authentication_token:
            return users
        headers = {
          "Content-Type": "application/json",
          "Authorization": f"JWT {self.authentication_token}"
        }
        users_url = f"{self.base_url}/api/v2/user/fcm-users"
        try:
            while users_url:
                response = requests.get(users_url, headers=headers)
                if response.status_code == 200:
                    data = json.loads(response.text)
                    users.extend(data.get('fcm_user_list'))
                    users_url = data.get('next')
                else:
                    break
        except Exception as e:
            print(f"Exception while getting users: {str(e)}")
        return users

    def deactivate_failed_fcm_tokens(self, fcm_ids):
        """
        Deactivate fcm of the failed token
        :param fcm_ids:
        :return: String
        """
        if len(fcm_ids):
            try:
                headers = {
                  "Content-Type": "application/json",
                  "Authorization": f"JWT {self.authentication_token}"
                }
                url = f"{self.base_url}/api/v2/fcm-token/bulk_deactivate/"
                requests.post(url, headers=headers, json={'ids': fcm_ids})
            except Exception as e:
                print(f"Exception while deactivating FCM user's token: {str(e)}")
            return "Success in deactivating users' token"
        return "No FCM token found to deactivate"

    def update_updated_at_of_success_fcm_tokens(self, fcm_ids):
        """
        Update the updated at date of the fcm so that they will be only checked every X days
        :param fcm_ids:
        :return: String
        """
        if len(fcm_ids):
            try:
                headers = {
                  "Content-Type": "application/json",
                  "Authorization": f"JWT {self.authentication_token}"
                }
                url = f"{self.base_url}/api/v2/fcm-token/bulk-update-on-updated/"
                requests.post(url, headers=headers, json={'ids': fcm_ids})
            except Exception as e:
                print(f"Exception while update the FCM updated_at date: {str(e)}")
            return "Success in updating the FCM updated_at date"
        return "No users found to update the FCM updated_at date"

    def get_failed_users_from_failed_tokens(self, failed_users, failed_user_id_dict_with_failed_platform):
        """
        Send the email to failed users
        :param failed_users: list of users with id, token_id, platform, full_name, email
        :param failed_user_id_dict_with_failed_platform: lists ot user_ids with failed platform
        :return: list of failed users with id, token_id, platform, full_name, email
        """

        existing_used_details = {}
        failed_user_details = []
        for user in failed_users:
            user_id = user.get('user_id')
            user_failed_platform = failed_user_id_dict_with_failed_platform.get(user_id, [])
            if user.get('platform') in user_failed_platform:
                if user_id not in existing_used_details:
                    existing_used_details[user_id] = []
                if user.get('platform') not in existing_used_details[user_id]:
                    failed_user_details.append({**user})
                    existing_used_details[user_id].append(user.get('platform'))
        return failed_user_details

    def save_unique_platform_in_user_dict(self, data_list: Dict[int, List[str]], platform: str, user_id: int):
        """
        Save the unique platform in the dict of users
        :param data_list: dict of users with list of unique platform or empty dict
        :param platform: str ->  token of user
        :return: dict of users with list of unique platform
        """

        if not data_list.get(user_id, []):
            data_list[user_id] = []
        if platform not in data_list[user_id]:
            data_list[user_id].append(platform)
