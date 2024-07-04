import json
import boto3
from botocore.exceptions import ClientError
import firebase_admin
from firebase_admin import credentials
import os

from firebase_admin import messaging

DIRS = 'dirs'
AEGIX = 'aegix'
DIRS_FCM_APP_NAME = 'dirs_fcm_app'
AEGIX_FCM_APP_NAME = 'aegix_fcm_app'

default_title = "Test Notification"
default_body = "This is test notification to see if the push notifications are valid"
default_secret_type = 'boto3'
default_chunk_size = 500
default_dry_run = False


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class FirebaseService:
    """
    Class for sending the push notifications using the Firebase API using multiple Firebase apps.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the FirebaseService instance.
        title (str): The title of the notification
        body (str): The body of the notification
        dry_run (bool): A boolean indicating whether to run the operation in dry run mode (optional).
        secret_method_type (str):  The type of the secret method (optional).
          - Default: boto3
        Returns:
            failed_tokens (list): List of failed tokens
        """
        self.firebase_secret_manager_region = os.environ.get('FIREBASE_SECRET_MANAGER_REGION', '')
        self.firebase_system_manager_name = os.environ.get('FIREBASE_SYSTEM_MANAGER_NAME', '')
        self.firebase_dirs_fcm_secret_name = os.environ.get('FIREBASE_DIRS_FCM_APP_SECRET_NAME', '')
        self.firebase_aegix_fcm_secret_name = os.environ.get('FIREBASE_AEGIX_FCM_APP_SECRET_NAME', '')
        self.title = kwargs.get('title', default_title)
        self.body = kwargs.get('body', default_body)
        self.chunk_size = kwargs.get('chunk_size', default_chunk_size)
        self.dry_run = kwargs.get('dry_run', default_dry_run)
        self.aegix_fcm_json = {}
        self.dirs_fcm_json = {}
        self.dirs_fcm_app = None
        self.aegix_fcm_app = None
        self.secret_method_type = kwargs.get('secret_type', default_secret_type)
        self.__create_app()

    def __get_default_secret(self):
        dirs_fcm = aegix_fcm = None
        self.dirs_fcm_json = dirs_fcm
        self.aegix_fcm_json = aegix_fcm

    def __get_secret_using_boto(self):
        self.get_data_from_system_manager()
        self.get_fcm_secret_credentials()

    def __get_secret(self):
        if self.secret_method_type == 'boto3':
            self.__get_secret_using_boto()
        else:
            self.__get_default_secret()

    def __create_app(self):
        self.__get_secret()
        if self.aegix_fcm_json:
            self.aegix_fcm_app = firebase_admin.initialize_app(credentials.Certificate(self.aegix_fcm_json),
                                                               name=AEGIX_FCM_APP_NAME)
        if self.dirs_fcm_json:
            self.dirs_fcm_app = firebase_admin.initialize_app(credentials.Certificate(self.dirs_fcm_json),
                                                              name=DIRS_FCM_APP_NAME)

    def get_data_from_secret_manager(self, secret_key):
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=self.firebase_secret_manager_region
        )
        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_key
            )
            secret_string = get_secret_value_response['SecretString']
            return json.loads(secret_string)
        except ClientError as e:
            message = f"Error in getting  secret details using boto3: Error {str(e)}"
            print(message)
        return {}

    def get_data_from_system_manager(self):
        ssm = boto3.client('ssm')
        response = ssm.get_parameter(Name=self.firebase_system_manager_name)
        try:
            data = response['Parameter']['Value']
            data_json = json.loads(data)
            self.aegix_fcm_json = data_json.get('project', {}).get('aegix_fcm', {})
            self.dirs_fcm_json = data_json.get('project', {}).get('dir-s-1373', {})
        except Exception as e:
            error_message = f'Error in getting data from system manager. Error: {str(e)}'
            print(error_message)
            raise Exception(error_message)

    def get_fcm_secret_credentials(self):
        fcm_details = [
            {
                'name': DIRS,
                'secret_name': self.firebase_dirs_fcm_secret_name
            }, {
                'name': AEGIX,
                'secret_name': self.firebase_aegix_fcm_secret_name
            }
        ]
        for fcm_detail in fcm_details:
            fcm_for = fcm_detail.get('name')
            fcm_secret = fcm_detail.get('secret_name')
            if fcm_for and fcm_secret:
                secret_json = self.get_data_from_secret_manager(fcm_secret)
                if not secret_json:
                    continue
                try:
                    client_id = secret_json.get('client_id')
                    private_key_id = secret_json.get('private_key_id')
                    private_key = secret_json.get('private_key').replace('\\n', '\n')
                    if fcm_for == DIRS:
                        self.dirs_fcm_json['client_id'] = client_id
                        self.dirs_fcm_json['private_key_id'] = private_key_id
                        self.dirs_fcm_json['private_key'] = private_key
                    elif fcm_for == AEGIX:
                        self.aegix_fcm_json['client_id'] = client_id
                        self.aegix_fcm_json['private_key_id'] = private_key_id
                        self.aegix_fcm_json['private_key'] = private_key
                except Exception as e:
                    error_message = f'Error in getting dirs fcm secret credentials. Error: {str(e)}'
                    print(error_message)
                    raise Exception(error_message)

    def send_batch_push_notification(self, message_obj, notification_app, users):
        invalid_tokens = []
        failed_tokens = []
        success_tokens = []
        internal_error_tokens = []
        for chunk in chunks(message_obj, self.chunk_size):
            try:
                batch_response = messaging.send_each(chunk, app=notification_app, dry_run=self.dry_run)
                print(
                    f'Message batch attempted: Count={len(chunk)}; '
                    f'Sent={batch_response.success_count}; '
                    f'Failed={batch_response.failure_count}; '
                )
                for i, response in enumerate(batch_response.responses):
                    if response.success:
                        success_tokens.append(chunk[i].token)
                    else:
                        if response.exception.code in [
                            'invalid-recipient',
                            'invalid-registration-token',
                            'registration-token-not-registered'
                        ]:
                            invalid_tokens.append(chunk[i].token)
                        elif response.exception.code == 'internal-error':
                            internal_error_tokens.append(chunk[i].token)
                        else:
                            failed_tokens.append(chunk[i].token)
            except Exception as e:
                message = f'Exception Sending Push notification. Exception: {str(e)}'
                print(message)
                raise Exception(message)
        failed_token_lists = invalid_tokens + failed_tokens + internal_error_tokens
        return failed_token_lists, success_tokens

    def send_push_notification_to_users(self, users):
        push_notification_apps_detail = []
        failed_tokens = []
        success_tokens = []
        if self.aegix_fcm_app:
            push_notification_apps_detail.append({
                'name': AEGIX,
                'app': self.aegix_fcm_app})
        if self.dirs_fcm_app:
            push_notification_apps_detail.append({
                'name': DIRS,
                'app': self.dirs_fcm_app})

        if not len(push_notification_apps_detail):
            print("No push notification apps is found")
            return failed_tokens, success_tokens

        dirs_tokens = []
        aegix_tokens = []
        dirs_message = []
        aegix_messages = []
        data = {
            "body": self.body
        }

        for user in users:
            if user.get('app_name') == DIRS:
                data['title'] = self.title.format('DIR-S')
                dirs_tokens.append(user)
                dirs_message.append(
                    messaging.Message(
                        token=user.get('token'),
                        data=data
                    )
                )
            else:
                data['title'] = self.title.format('Aegix AIM')
                aegix_tokens.append(user)
                aegix_messages.append(
                    messaging.Message(
                        token=user.get('token'),
                        data=data
                    )
                )
        for push_notification_app_detail in push_notification_apps_detail:
            push_notification_app = push_notification_app_detail.get('app')
            app_type = push_notification_app_detail.get('name')
            if app_type == DIRS:
                messages = dirs_message
            else:
                messages = aegix_messages
            _failed_tokens, _success_tokens = self.send_batch_push_notification(messages, push_notification_app, users)
            failed_tokens.extend(_failed_tokens)
            success_tokens.extend(_success_tokens)
        return list(set(failed_tokens)), list(set(success_tokens))
