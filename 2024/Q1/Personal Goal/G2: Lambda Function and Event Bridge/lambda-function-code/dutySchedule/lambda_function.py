import json
import os
import requests

from core.authenticate import UserAuthenticate
from schedule.schedule import TimeSchedule
from userduty.userduty import UserDuty

def lambda_handler(event, context):

    authenticate = UserAuthenticate()
    token = authenticate.authenticate()

    userduty_obj = UserDuty(token)
    userduty_obj.update_user_duty_status()

    return {
        'statusCode': 200,
        'body': json.dumps("Success.")
    }

lambda_handler(None, None)