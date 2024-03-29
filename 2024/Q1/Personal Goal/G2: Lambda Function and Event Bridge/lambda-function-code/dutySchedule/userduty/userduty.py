import datetime
import json
import os
import requests

from pytz import timezone

from schedule.schedule import TimeSchedule


class UserDuty:
    def __init__(self, authentication_token=None, *args, **kwargs):
        self.base_url = os.environ['BASE_API_URL']
        self.authentication_token = authentication_token
        self.user_duty_url = f"{self.base_url}/api/v2/user-duty/bulk-update/"

    def __update_off_duty_status(self, user_duty_ids_off=None):
        if not self.authentication_token:
            print("Authentication token not found.")
            return False
        
        print('off duty status')
        
        if not user_duty_ids_off:
            print("No user IDs to update.")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"JWT {self.authentication_token}"
        }

        payload = {
            "user_duty_ids": user_duty_ids_off,
            'is_on_duty': False
        }

        try:
            response = requests.put(self.user_duty_url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                print(f"User duty status updated successfully for user IDs {user_duty_ids_off}.")
                return True
            else:
                print(f"Failed to update user duty status for user IDs {user_duty_ids_off}.")
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.text}")
                return False
        except Exception as e:
            print(f"An error occurred while updating user duty status for user IDs {user_duty_ids_off}: {str(e)}")
            return False

        return True
    
    def __update_on_duty_status(self, user_duty_ids_on=None):
        if not self.authentication_token:
            print("Authentication token not found.")
            return False
        
        print('off duty status')
        
        if not user_duty_ids_on:
            print("No user IDs to update.")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"JWT {self.authentication_token}"
        }

        payload = {
            "user_duty_ids": user_duty_ids_on,
            'is_on_duty': True
        }

        try:
            response = requests.put(self.user_duty_url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                print(f"User duty status updated successfully for user IDs {user_duty_ids_on}.")
                return True
            else:
                print(f"Failed to update user duty status for user IDs {user_duty_ids_on}.")
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.text}")
                return False
        except Exception as e:
            print(f"An error occurred while updating user duty status for user IDs {user_duty_ids_on}: {str(e)}")
            return False
        return True

    def update_user_duty_status(self):
        if not self.authentication_token:
            print("Authentication token not found.")
            return False

        schedule_obj = TimeSchedule(self.authentication_token)
        user_duty_ids_on_and_off_schedule = schedule_obj.get_user_duty_ids_on_and_off_schedule()
        # print(user_duty_ids_on_and_off_schedule, 'user_duty_ids_on_and_off_schedule')

        # separate user ids that need to be on and off
        user_duty_ids_off = user_duty_ids_on_and_off_schedule.get('is_off_duty_list', [])
        if len(user_duty_ids_off):
            self.__update_off_duty_status(user_duty_ids_off)

        user_duty_ids_on = user_duty_ids_on_and_off_schedule.get('is_on_duty_list', [])
        if len(user_duty_ids_on):
            self.__update_on_duty_status(user_duty_ids_on)

        return True
