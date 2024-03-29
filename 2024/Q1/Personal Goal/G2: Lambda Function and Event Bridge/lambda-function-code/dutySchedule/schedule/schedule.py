import datetime
import json
import os
import requests

from pytz import timezone

class TimeSchedule:

    def __init__(self, authentication_token=None, *args, **kwargs):
        self.base_url = os.environ['BASE_API_URL']
        self.authentication_token = authentication_token

    def __get_current_time(self):
        return datetime.datetime.now(timezone(os.environ['TIMEZONE']))
    
    def __get_user_duty_ids_for_on_and_off_schedule(self, current_time, schedule_list):
        # list need to set off duty
        is_off_duty_list = list()

        # list need to set on duty
        is_on_duty_list = list()
        current_time = datetime.datetime.strptime(current_time, "%H:%M").time()

        for schedule in schedule_list:
            schedule_start_time = datetime.datetime.strptime(schedule['start_time'], "%H:%M:%S").time().replace(second=0)
            schedule_end_time = datetime.datetime.strptime(schedule['end_time'], "%H:%M:%S").time().replace(second=0)

            is_on_duty = schedule['is_on_duty']

            if schedule_start_time == current_time:
                if is_on_duty is False:
                    is_on_duty_list.append(schedule['user_duty_id'])

            elif schedule_end_time == current_time:
                if is_on_duty is True:
                    is_off_duty_list.append(schedule['user_duty_id'])
        return {
            'is_off_duty_list': is_off_duty_list,
            'is_on_duty_list': is_on_duty_list
            }

    def __get_schedule_list(self, current_day, current_time):
        if not self.authentication_token:
            print('no authentication token')
            return []
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"JWT {self.authentication_token}"
        }

        schedule_url = f"{self.base_url}/api/v2/schedule/?days_of_week={current_day}&time={current_time}"

        schedule_list = []
        while schedule_url:
            response = requests.get(schedule_url, headers=headers)
            if response.status_code == 200:
                data = json.loads(response.text)
                schedule_list.extend(data.get('results'))
                schedule_url = data.get('next')
            else:
                break
        return schedule_list
    
    def get_user_duty_ids_on_and_off_schedule(self):
        if not self.authentication_token:
            print('no authentication token')
            return []
        
        current_time_obj = self.__get_current_time()
        current_day = current_time_obj.strftime("%a").upper()
        current_time = current_time_obj.strftime("%H:%M")

        schedule_list = self.__get_schedule_list(current_day, current_time)

        return self.__get_user_duty_ids_for_on_and_off_schedule(current_time, schedule_list)
    