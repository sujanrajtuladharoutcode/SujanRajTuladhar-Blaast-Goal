from firebaseService import FirebaseService
from userService import UserService
from emailService import EmailService

title = "{} Push Notification Test"
body = "This is push notification to validate this device's token. No further action is needed."
chunk_size = 500


def lambda_handler(event, context):
    user_service = UserService()
    fcm_user_tokens = user_service.authenticate().get_fcm_tokens()
    if len(fcm_user_tokens):
        firebase = FirebaseService(title=title, body=body, chunk_size=chunk_size, dry_run=True, secret_type='boto3')
        failed_tokens, success_tokens = firebase.send_push_notification_to_users(fcm_user_tokens)
        failed_fcm_tokens_list = []
        failed_fcm_user_lists = []
        failed_user_id_dict_with_failed_platform = {}
        success_fcm_ids = []
        success_user_id_dict_with_success_platform = {}
        user_id_dict_with_all_platform = {}
        for fcm_user_token in fcm_user_tokens:
            user_id = fcm_user_token.get('user_id')
            if fcm_user_token.get('token') in success_tokens:
                user_service.save_unique_platform_in_user_dict(success_user_id_dict_with_success_platform,
                                                               fcm_user_token.get('platform'), user_id)
                success_fcm_ids.append(fcm_user_token.get('token'))

        for fcm_user_token in fcm_user_tokens:
            user_id = fcm_user_token.get('user_id')
            if fcm_user_token.get('platform') not in success_user_id_dict_with_success_platform.get(user_id, []):
                failed_fcm_tokens_list.append(fcm_user_token.get('token'))
                failed_fcm_user_lists.append(fcm_user_token)
                user_service.save_unique_platform_in_user_dict(failed_user_id_dict_with_failed_platform,
                                                               fcm_user_token.get('platform'), user_id)

            user_service.save_unique_platform_in_user_dict(user_id_dict_with_all_platform, fcm_user_token.get('platform'),
                                                           user_id)

        failed_fcm_token_update_response = user_service.deactivate_failed_fcm_tokens(failed_fcm_tokens_list)
        print(failed_fcm_token_update_response)

        update_at_fcm_token_update_response = user_service.update_updated_at_of_success_fcm_tokens(success_fcm_ids)
        print(update_at_fcm_token_update_response)

        failed_users = user_service.get_failed_users_from_failed_tokens(failed_fcm_user_lists,
                                                                        failed_user_id_dict_with_failed_platform)
        print(failed_users)

        if len(failed_users):
            email_service = EmailService(receivers=failed_users)
            email_service.send_email()
    else:
        print(f'No users found')
