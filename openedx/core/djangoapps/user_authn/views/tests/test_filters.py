"""
Test that various filters are fired for the vies in the user_authn app.
"""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from openedx_filters import PipelineStep
from openedx_filters.learning.auth import PreLoginFilter, PreRegisterFilter
from rest_framework import status

from common.djangoapps.student.tests.factories import UserFactory, UserProfileFactory
from openedx.core.djangoapps.user_api.tests.test_views import UserAPITestCase
from openedx.core.djangolib.testing.utils import skip_unless_lms


class TestRegisterPipelineStep(PipelineStep):
    """
    Utility function used when getting steps for pipeline.
    """

    def run(self, form_data):  # pylint: disable=arguments-differ
        """Pipeline steps that changes the user's username."""
        username = f"{form_data.get('username')}-OpenEdx"
        form_data["username"] = username
        return {
            "form_data": form_data,
        }


class TestStopRegisterPipelineStep(PipelineStep):
    """
    Utility function used when getting steps for pipeline.
    """

    def run(self, form_data):  # pylint: disable=arguments-differ
        """Pipeline steps that changes the user's username."""
        raise PreRegisterFilter.PreventRegister("You can't register on this site.", status_code=403)


class TestLoginPipelineStep(PipelineStep):
    """
    Utility function used when getting steps for pipeline.
    """

    def run(self, user):
        """Pipeline steps that changes the user's username."""
        user.profile.set_meta({"logged_in": True})
        user.profile.save()
        return {
            "user": user
        }


class TestStopLoginPipelineStep(PipelineStep):
    """
    Utility function used when getting steps for pipeline.
    """

    def run(self, user):
        """Pipeline steps that changes the user's username."""
        raise PreLoginFilter.PreventLogin("You can't login on this site.")


@skip_unless_lms
class RegistrationFiltersTest(UserAPITestCase):
    """
    Tests for the Open edX Filters associated with the user login process.

    This class guarantees that the following filters are triggered during the user's login:

    - PreLoginFilter
    """

    def setUp(self):  # pylint: disable=arguments-differ
        super().setUp()
        self.url = reverse("user_api_registration")
        self.user_info = {
            "email": "user@example.com",
            "name": "Test User",
            "username": "test",
            "password": "password",
            "honor_code": "true",
        }

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.student.registration.requested.v1": {
                "pipeline": [
                    "openedx.core.djangoapps.user_authn.views.tests.test_filters.TestRegisterPipelineStep",
                ],
                "fail_silently": False,
            },
        },
    )
    def test_register_filter_executed(self):
        """
        Test whether the student enrollment filter is triggered before the user's
        enrollment process.

        Expected result:
            - PreLoginFilter is triggered and executes TestLoginPipelineStep.
            - The arguments that the receiver gets are the arguments used by the filter
            with the enrollment mode changed.
        """
        self.client.post(self.url, self.user_info)

        user = User.objects.filter(username=f"{self.user_info.get('username')}-OpenEdx")
        self.assertTrue(user)

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.student.registration.requested.v1": {
                "pipeline": [
                    "openedx.core.djangoapps.user_authn.views.tests.test_filters.TestStopRegisterPipelineStep",
                ],
                "fail_silently": False,
            },
        },
    )
    def test_register_filter_prevent_registration(self):
        """
        Test prevent the user's enrollment through a pipeline step.

        Expected result:
            - PreLoginFilter is triggered and executes TestStopLoginPipelineStep.
            - The user can't enroll.
        """
        response = self.client.post(self.url, self.user_info)

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)


@skip_unless_lms
class LoginFiltersTest(UserAPITestCase):
    """
    Tests for the Open edX Filters associated with the user login process.

    This class guarantees that the following filters are triggered during the user's login:

    - PreLoginFilter
    """

    def setUp(self):  # pylint: disable=arguments-differ
        super().setUp()
        self.user = UserFactory.create(
            username="test",
            email="test@example.com",
            password="password",
        )
        self.user_profile = UserProfileFactory.create(user=self.user, name="Test Example")
        self.url = reverse('login_api')

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.student.login.requested.v1": {
                "pipeline": [
                    "openedx.core.djangoapps.user_authn.views.tests.test_filters.TestLoginPipelineStep",
                ],
                "fail_silently": False,
            },
        },
    )
    def test_login_filter_executed(self):
        """
        Test whether the student enrollment filter is triggered before the user's
        enrollment process.

        Expected result:
            - PreLoginFilter is triggered and executes TestLoginPipelineStep.
            - The arguments that the receiver gets are the arguments used by the filter
            with the enrollment mode changed.
        """
        data = {
            "email": "test@example.com",
            "password": "password",
        }

        self.client.post(self.url, data)

        user = User.objects.get(username=self.user.username)
        self.assertDictEqual({"logged_in": True}, user.profile.get_meta())

    @override_settings(
        OPEN_EDX_FILTERS_CONFIG={
            "org.openedx.learning.student.login.requested.v1": {
                "pipeline": [
                    "openedx.core.djangoapps.user_authn.views.tests.test_filters.TestStopLoginPipelineStep",
                ],
                "fail_silently": False,
            },
        },
    )
    def test_login_filter_prevent_login(self):
        """
        Test prevent the user's enrollment through a pipeline step.

        Expected result:
            - PreLoginFilter is triggered and executes TestStopLoginPipelineStep.
            - The user can't enroll.
        """
        data = {
            "email": "test@example.com",
            "password": "password",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
