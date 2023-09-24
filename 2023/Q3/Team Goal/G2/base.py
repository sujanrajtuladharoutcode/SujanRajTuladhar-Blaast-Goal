import factory.random
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from channels.testing import WebsocketCommunicator

from server.apps.accounts.factories import BaseUserFactory
from server.apps.schools.factories import RoomFactory
from server.apps.accounts.models import BaseUser as User
from server.api.v2.serializers import UserSerializer
from server.api.permissions import PublicApiAccess
import types

class TestClasses:
    class ModelTests(APITestCase):
        """
        Base class for testing Django models and REST APIs.

        This class provides common methods and attributes for testing Django models and REST APIs for those models.
        Subclasses can inherit from this class and define their specific tests.

        Attributes:
            Model (class): The Django model class to be tested.
            ModelFactory (class): The factory class to create instances of the model.
            ModelSerializer (class): The serializer class for the model.
            url_prefix (str): The URL prefix for the model's API endpoints.
            _change_key (str): A key to identify changes in model data during updates.
            allow_create_own (bool): Flag indicating whether users can create their own instances of the model.
            has_sockets (bool): Flag indicating whether the model has WebSocket support.
            current_user (User): The currently authenticated user during tests.
            uses_soft_delete (bool): Flag indicating whether the model uses soft deletion.

        Methods:
            check_socket_for: Connects to WebSocket and checks for messages.
            change_key: Returns the key used to identify changes during updates.
            get_model_kwargs: Returns additional keyword arguments for creating model instances.
            get_instance: Creates and returns an instance of the model.
            get_model_dict: Returns a dictionary representation of a model instance.
            clean_model_dict: Cleans up a model dictionary by removing None values and converting model objects to IDs.
            set_user: Sets the currently authenticated user for testing.
        """
        
        Model = User
        ModelFactory = BaseUserFactory
        ModelSerializer = UserSerializer
        url_prefix = 'user'
        _change_key = None
        allow_create_own = False
        has_sockets = True
        current_user = None
        uses_soft_delete = False

        def check_socket_for(self, trigger, on_message):
            """
            Connects to WebSocket and checks for messages.

            Args:
                trigger (function): A function to trigger a WebSocket event.
                on_message (function): A function to handle WebSocket messages.

            This method connects to a WebSocket and waits for messages. It triggers the WebSocket event using the
            `trigger` function and handles messages using the `on_message` function.
            """
                       
            from server.api.v2.consumers import EverythingConsumer
            import asyncio

            loop = asyncio.get_event_loop()
            def sync_await(future):
                return loop.run_until_complete(future)

            communicator = WebsocketCommunicator(EverythingConsumer, "/api/v2/ws/")
            communicator.scope["user"] = self.current_user
            sync_await(communicator.connect())

            response_promise = communicator.receive_json_from()
            trigger()
            while True:
                try:
                    response = sync_await(response_promise)
                    if response.get('type') == self.socket_type:
                        on_message(response)
                        break
                    elif response is None:
                        break
                    else:
                        response_promise = communicator.receive_json_from()
                except:
                    break

            sync_await(communicator.disconnect())

        def change_key(self, data):
            """
            Returns the key to identify changes in model data during updates.

            Args:
                data (dict): The data dictionary representing the model instance.

            Returns:
                str: The key to identify changes in data.
            """
                        
            return self._change_key or list(data)[-1]

        def get_model_kwargs(self):
            """
            Returns additional keyword arguments for creating model instances.

            Returns:
                dict: Additional keyword arguments for creating model instances.
            """

            return {'school': self.default_school}

        def get_instance(self, **kwargs):
            """
            Creates and returns an instance of the model.

            Args:
                **kwargs: Additional keyword arguments to customize the instance.

            Returns:
                Model: An instance of the model.
            """

            all_dict = {}
            all_dict.update(self.get_model_kwargs())
            all_dict.update(kwargs)
            return self.ModelFactory(**all_dict)

        def get_model_dict(self):
            """
            Returns a dictionary representation of a model instance.

            Returns:
                dict: A dictionary representation of a model instance.
            """

            return model_to_dict(self.ModelFactory.build(**self.get_model_kwargs()))

        def clean_model_dict(self, data):
            """
            Cleans up a model dictionary.

            Args:
                data (dict): The data dictionary representing the model instance.

            Returns:
                dict: The cleaned-up data dictionary.
            """

            data = {k: v for (k, v) in data.items() if v is not None and k in self.serializer_fields}
            data = {k: v.id if isinstance(v, models.Model) else v for (k, v) in data.items()}
            if 'school' in self.serializer_fields:
                data['school'] = self.default_school.id

            if 'pending_approval_status' in self.serializer_fields:
                data['pending_approval_status'] = self.update_pending_approval_status
            return data

        def set_user(self, user):
            """
            Sets the currently authenticated user for testing.

            Args:
                user (User): The user to authenticate.
            """

            self.client.force_authenticate(user)
            self.current_user = user

        def setUp(self):
            """
            Sets up the test environment before running each test method.

            This method is called before running each test method. It sets up the necessary permissions and users for
            testing.
            """

            if getattr(self, 'socket_type', None) is None:
                self.socket_type = self.Model.__name__
            content_type = ContentType.objects.get_for_model(self.Model)
            view_perm = Permission.objects.get(
                codename='view_' + content_type.model
            )
            add_perm = Permission.objects.get(
                codename='add_' + content_type.model
            )
            change_perm = Permission.objects.get(
                codename='change_' + content_type.model
            )
            delete_perm = Permission.objects.get(
                codename='delete_' + content_type.model
            )
            view_deleted_perm = Permission.objects.get(
                codename='view_deleted_objects'
            )
            api_perm = Permission.objects.get(codename="can_use_public_api")
            alert_perm = Permission.objects.get(codename="add_alert")
            factory.random.reseed_random('resource model tests')
            self.default_school = RoomFactory().floor.building.school

            self.admin_user = BaseUserFactory(is_superuser=True)
            self.admin_user.save()
            self.admin_user.user_permissions.add(api_perm)
            self.admin_user.user_permissions.add(alert_perm)
            self.admin_user.user_permissions.add(view_perm)
            self.admin_user.user_permissions.add(add_perm)
            self.admin_user.user_permissions.add(change_perm)
            self.admin_user.user_permissions.add(delete_perm)
            self.admin_user.user_permissions.add(view_deleted_perm)
            self.admin_user.schools.add(self.default_school)
            self.admin_user = User.objects.get(pk=self.admin_user.pk)

            self.semi_admin_user = BaseUserFactory(is_superuser=False)
            self.semi_admin_user.save()
            self.semi_admin_user.user_permissions.add(api_perm)
            self.semi_admin_user.user_permissions.add(alert_perm)
            self.semi_admin_user.user_permissions.add(view_perm)
            self.semi_admin_user.user_permissions.add(add_perm)
            self.semi_admin_user.user_permissions.add(change_perm)
            self.semi_admin_user.user_permissions.add(delete_perm)
            self.semi_admin_user.user_permissions.add(view_deleted_perm)
            self.semi_admin_user.schools.add(self.default_school)
            self.semi_admin_user = User.objects.get(pk=self.semi_admin_user.pk)

            self.base_user = BaseUserFactory(is_superuser=False, user_type='teacher')
            self.base_user.save()
            self.base_user.user_permissions.add(api_perm)
            self.base_user.user_permissions.add(alert_perm)
            self.base_user.user_permissions.add(view_perm)
            self.base_user.schools.add(self.default_school)
            self.base_user = User.objects.get(pk=self.base_user.pk)

            self.set_user(self.admin_user)
            self.serializer_fields = set(self.ModelSerializer().fields.keys())

        def test_list_admin(self):
            """
            Test listing instances by an admin user.

            This test checks if an admin user can list instances of the model.
            """
            self.get_instance()

            response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(len(response.data['results']), self.Model.objects.count(), response.data)

        def test_create_admin(self):
            """
            Ensure we can create a new {}
            """.format(self.Model._meta.verbose_name)
            original = self.Model.objects.count()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)
            response = self.client.post(reverse('v2:{}-list'.format(self.url_prefix)), data)
            self.assertEqual(response.status_code,
                             status.HTTP_201_CREATED, response.data)
            self.assertEqual(self.Model.objects.count(), original + 1)

        def test_retrieve_admin(self):
            """
            Test retrieving an instance by an admin user.

            This test checks if an admin user can retrieve an instance of the model.
            """

            model = self.get_instance()
            original_count = self.Model.objects.count()
            response = self.client.get(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(self.Model.objects.count(), original_count)

        def test_update_admin(self):
            """
            Test updating an instance by an admin user.

            This test checks if an admin user can update an instance of the model.
            """

            model = self.get_instance()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)
            key = self.change_key(data)
            self.set_user(self.admin_user)
            self.assertNotEqual(data[key], getattr(model, key), "Update data same as model data. Key: {}".format(key))
            response = self.client.put(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}), data, format='multipart')
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)

            self.assertEqual(
                data[key], response.data[key], response.data)

        def test_socket_update(self):
            """
            Test WebSocket update for an instance.

            This test checks if WebSocket updates for an instance work correctly.
            """

            if not self.has_sockets:
                return
            model = self.get_instance()
            data = types.SimpleNamespace(got_message=False)
            def trigger():
                data = self.get_model_dict()
                data = self.clean_model_dict(data)
                key = self.change_key(data)
                self.client.patch(reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}), data)
            def on_message(x):
                data.got_message = True
            self.check_socket_for(trigger, on_message)
            self.assertTrue(data.got_message)

        def test_partial_update_admin(self):
            """
            Test partially updating an instance by an admin user.

            This test checks if an admin user can partially update an instance of the model.
            """

            model = self.get_instance()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)
            key = self.change_key(data)
            self.assertNotEqual(data[key], getattr(model, key), "Update data same as model data. Key: {}".format(key))

            self.set_user(self.admin_user)
            response = self.client.patch(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}), data)
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(response.data[key], data[key], key)

        def test_delete_admin(self):
            """
            Test deleting an instance by an admin user.

            This test checks if an admin user can delete an instance of the model.
            """

            model = self.get_instance()

            response = self.client.delete(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_204_NO_CONTENT, response.data)

            if self.uses_soft_delete:
                model_updated = self.Model.all_objects.get(pk=model.pk)
                self.assertIsNotNone(model_updated.deleted)
            else:
                self.assertEqual(self.Model.objects.filter(pk=model.pk).count(), 0)

        def test_soft_delete_filter_admin(self):
            """
            Test filtering soft deleted instances by an admin user.

            This test checks if an admin user can filter soft deleted instances of the model.
            """

            if self.uses_soft_delete:
                model = self.get_instance()

                response = self.client.delete(
                    reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
                self.assertEqual(response.status_code,
                                 status.HTTP_204_NO_CONTENT, response.data)

                response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)))
                self.assertEqual(response.status_code,
                                 status.HTTP_200_OK, response.data)
                self.assertEqual(len(response.data['results']), self.Model.all_objects.count())

                response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)) + '?deleted=true')
                self.assertEqual(response.status_code,
                                 status.HTTP_200_OK, response.data)
                self.assertEqual(len(response.data['results']), self.Model.all_objects.filter(deleted__isnull=False).count())

                response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)) + '?deleted=false')
                self.assertEqual(response.status_code,
                                 status.HTTP_200_OK, response.data)
                self.assertEqual(len(response.data['results']), self.Model.all_objects.filter(deleted__isnull=True).count())

        def test_list_base(self):
            """
            Test listing instances by a base user.

            This test checks if a base user can list instances of the model.
            """

            self.set_user(self.base_user)
            self.get_instance()

            response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(len(response.data['results']), self.Model.objects.count())

        def test_create_base(self):
            """
            Ensure users without permission can't create a new {}
            """.format(self.Model._meta.verbose_name)
            self.set_user(self.base_user)
            original_count = self.Model.objects.count()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)
            
            response = self.client.post(reverse('v2:{}-list'.format(self.url_prefix)), data)
            if self.allow_create_own:
                self.assertEqual(response.status_code,
                                 status.HTTP_201_CREATED, response.data)
                self.assertEqual(self.Model.objects.count(), original_count + 1)
            else:
                self.assertEqual(response.status_code,
                                 status.HTTP_403_FORBIDDEN, response.data)
                self.assertEqual(self.Model.objects.count(), original_count)

        def test_retrieve_base(self):
            """
            Test retrieving an instance by a base user.

            This test checks if a base user can retrieve an instance of the model.
            """

            self.set_user(self.base_user)
            model = self.get_instance()
            original_count = self.Model.objects.count()
            response = self.client.get(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(self.Model.objects.count(), original_count)

        def test_update_base(self):
            """
            Test updating an instance by a base user.

            This test checks if a base user can update an instance of the model.
            """

            self.set_user(self.base_user)
            model = self.get_instance()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)

            response = self.client.put(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}), data)
            self.assertEqual(response.status_code,
                             status.HTTP_403_FORBIDDEN, response.data)

        def test_partial_update_base(self):
            """
            Test partially updating an instance by a base user.

            This test checks if a base user can partially update an instance of the model.
            """

            self.set_user(self.base_user)
            model = self.get_instance()
            data = self.get_model_dict()
            data = self.clean_model_dict(data)
            key = self.change_key(data)

            response = self.client.patch(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}), data)
            self.assertEqual(response.status_code,
                             status.HTTP_403_FORBIDDEN, response.data)

        def test_delete_base(self):
            """
            Test deleting an instance by a base user.

            This test checks if a base user can delete an instance of the model.
            """

            self.set_user(self.base_user)
            model = self.get_instance()

            response = self.client.delete(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_403_FORBIDDEN, response.data)

    class ReadOnlyModelTests(APITestCase):
        """
        Base class for testing read-only Django models and REST APIs.

        This class provides common methods and attributes for testing read-only Django models and REST APIs for those models.
        Subclasses can inherit from this class and define their specific tests.

        Attributes:
            Model (class): The Django read-only model class to be tested.
            ModelFactory (class): The factory class to create instances of the model.
            ModelSerializer (class): The serializer class for the model.
            url_prefix (str): The URL prefix for the model's API endpoints.

        Methods:
            get_model_kwargs: Returns additional keyword arguments for creating model instances.
            get_instance: Creates and returns an instance of the model.
            set_user: Sets the currently authenticated user for testing.
        """

        Model = User
        ModelFactory = BaseUserFactory
        ModelSerializer = UserSerializer
        url_prefix = 'user'

        def get_model_kwargs(self):
            """
            Returns additional keyword arguments for creating model instances.

            Returns:
                dict: Additional keyword arguments for creating model instances.
            """

            return {'school': self.default_school}

        def get_instance(self):
            """
            Creates and returns an instance of the read-only model.

            Returns:
                Model: An instance of the read-only model.
            """

            return self.ModelFactory(**self.get_model_kwargs())

        def set_user(self, user):
            """
            Sets the currently authenticated user for testing.

            Args:
                user (User): The user to authenticate.
            """

            self.client.force_authenticate(user)
            self.current_user = user

        def setUp(self):
            """
            Sets up the test environment before running each test method.

            This method is called before running each test method. It sets up the necessary permissions and users for
            testing.
            """

            content_type = ContentType.objects.get_for_model(self.Model)
            view_perm = Permission.objects.get(
                codename__startswith='view_',
                content_type=content_type
            )
            api_perm = Permission.objects.get(codename="can_use_public_api")
            factory.random.reseed_random('resource model tests')
            self.default_school = RoomFactory().floor.building.school
            self.admin_user = BaseUserFactory(is_superuser=True)
            self.admin_user.user_permissions.set([api_perm, view_perm])
            self.admin_user.schools.add(self.default_school)
            self.base_user = BaseUserFactory(is_superuser=False, user_type='teacher')
            self.base_user.user_permissions.set([api_perm])
            self.base_user.schools.add(self.default_school)
            self.set_user(self.admin_user)

        def test_list_admin(self):
            """
            Test listing instances by an admin user.

            This test checks if an admin user can list instances of the read-only model.
            """

            self.get_instance()

            response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(len(response.data['results']), self.Model.objects.count(), response.data)

        def test_retrieve_admin(self):
            """
            Test retrieving an instance by an admin user.

            This test checks if an admin user can retrieve an instance of the read-only model.
            """

            model = self.get_instance()
            original_count = self.Model.objects.count()
            response = self.client.get(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_200_OK, response.data)
            self.assertEqual(self.Model.objects.count(), original_count)

        def test_list_base(self):
            """
            Test listing instances by a base user.

            This test checks if a base user can list instances of the read-only model.
            """

            self.set_user(self.base_user)
            self.get_instance()

            response = self.client.get(reverse('v2:{}-list'.format(self.url_prefix)))
            self.assertEqual(response.status_code,
                             status.HTTP_403_FORBIDDEN, response.data)

        def test_retrieve_base(self):
            """
            Test retrieving an instance by a base user.

            This test checks if a base user can retrieve an instance of the read-only model.
            """
            
            self.set_user(self.base_user)
            model = self.get_instance()
            original_count = self.Model.objects.count()
            response = self.client.get(
                reverse('v2:{}-detail'.format(self.url_prefix), kwargs={"pk": model.pk}))
            self.assertEqual(response.status_code,
                             status.HTTP_403_FORBIDDEN, response.data)
