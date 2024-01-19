""" Common Authentication Handlers used across projects. """

import logging

import django.utils.timezone
from crum import get_current_request
from django.conf import settings
from oauth2_provider import models as dot_models
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from edx_django_utils.monitoring import set_custom_attribute

OAUTH2_TOKEN_ERROR = 'token_error'
OAUTH2_TOKEN_ERROR_EXPIRED = 'token_expired'
OAUTH2_TOKEN_ERROR_MALFORMED = 'token_malformed'
OAUTH2_TOKEN_ERROR_NONEXISTENT = 'token_nonexistent'
OAUTH2_TOKEN_ERROR_NOT_PROVIDED = 'token_not_provided'
OAUTH2_USER_NOT_ACTIVE_ERROR = 'user_not_active'
OAUTH2_USER_DISABLED_ERROR = 'user_is_disabled'


logger = logging.getLogger(__name__)


class OriginalBearerAuthentication(BaseAuthentication):
    """
    BearerAuthentication backend using either `django-oauth2-provider` or 'django-oauth-toolkit'
    """

    www_authenticate_realm = 'api'

    # currently, active users are users that confirm their email.
    # a subclass could override `allow_inactive_users` to enable access without email confirmation,
    # like in the case of mobile users.
    allow_inactive_users = False

    def authenticate(self, request):
        """
        Returns tuple (user, token) if access token authentication  succeeds,
        returns None if the user did not try to authenticate using an access
        token, or raises an AuthenticationFailed (HTTP 401) if authentication
        fails.
        """

        set_custom_attribute("BearerAuthentication", "Failed")  # default value
        auth = get_authorization_header(request).split()

        if len(auth) == 1:  # lint-amnesty, pylint: disable=no-else-raise
            raise AuthenticationFailed({
                'error_code': OAUTH2_TOKEN_ERROR_NOT_PROVIDED,
                'developer_message': 'Invalid token header. No credentials provided.'})
        elif len(auth) > 2:
            raise AuthenticationFailed({
                'error_code': OAUTH2_TOKEN_ERROR_MALFORMED,
                'developer_message': 'Invalid token header. Token string should not contain spaces.'})

        if auth and auth[0].lower() == b'bearer':
            access_token = auth[1].decode('utf8')
        else:
            set_custom_attribute("BearerAuthentication", "None")
            return None

        user, token = self.authenticate_credentials(access_token)

        set_custom_attribute("BearerAuthentication", "Success")

        return user, token

    def authenticate_credentials(self, access_token):
        """
        Authenticate the request, given the access token.

        Overrides base class implementation to discard failure if user is
        inactive.
        """

        try:
            token = self.get_access_token(access_token)
        except AuthenticationFailed as exc:
            raise AuthenticationFailed({  # lint-amnesty, pylint: disable=raise-missing-from
                'error_code': OAUTH2_TOKEN_ERROR,
                'developer_message': exc.detail
            })

        if not token:  # lint-amnesty, pylint: disable=no-else-raise
            raise AuthenticationFailed({
                'error_code': OAUTH2_TOKEN_ERROR_NONEXISTENT,
                'developer_message': 'The provided access token does not match any valid tokens.'
            })
        elif token.expires < django.utils.timezone.now():
            raise AuthenticationFailed({
                'error_code': OAUTH2_TOKEN_ERROR_EXPIRED,
                'developer_message': 'The provided access token has expired and is no longer valid.',
            })
        else:
            user = token.user
            has_application = dot_models.Application.objects.filter(user_id=user.id)
            if not user.has_usable_password() and not has_application:
                msg = 'User disabled by admin: %s' % user.get_username()
                raise AuthenticationFailed({
                    'error_code': OAUTH2_USER_DISABLED_ERROR,
                    'developer_message': msg})

            # Check to make sure the users have activated their account (by confirming their email)
            if not self.allow_inactive_users and not user.is_active:  # lint-amnesty, pylint: disable=no-else-raise
                set_custom_attribute("BearerAuthentication_user_active", False)
                msg = 'User inactive or deleted: %s' % user.get_username()
                raise AuthenticationFailed({
                    'error_code': OAUTH2_USER_NOT_ACTIVE_ERROR,
                    'developer_message': msg})
            else:
                set_custom_attribute("BearerAuthentication_user_active", True)

            return user, token

    def get_access_token(self, access_token):
        """
        Return a valid access token stored by django-oauth-toolkit (DOT), or
        None if no matching token is found.
        """
        token_query = dot_models.AccessToken.objects.select_related('user')
        return token_query.filter(token=access_token).first()

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response
        """
        return 'Bearer realm="%s"' % self.www_authenticate_realm


class BearerAuthentication(OriginalBearerAuthentication):
    """This new implementation just overrides some OriginalBearerAuthentication functionalities
    in order to include eduNEXT authentication requirements.
    """

    def get_access_token(self, access_token):
        """This override is required since the tokens should just be valid in the application's site,
        hence the token is restricted to the current url and the application redirect uris.

        Since some exception are required the 'ALLOWED_AUTH_APPLICATIONS' setting has been added, the
        applications, which are in the list, won't be restricted to the site.
        """
        token = super().get_access_token(access_token)
        current_url = get_current_request().build_absolute_uri('/')
        allowed_applications = getattr(settings, 'ALLOWED_AUTH_APPLICATIONS', [])

        if not token:
            return None

        application_name = token.application.name

        if token.application.redirect_uri_allowed(current_url) or application_name in allowed_applications:
            return token

        logger.warning(
            'The application <%s> has not been configured with the url <%s>',
            application_name,
            current_url,
        )

        return None


class BearerAuthenticationAllowInactiveUser(BearerAuthentication):
    """
    Currently, is_active field on the user is coupled
    with whether or not the user has verified ownership of their claimed email address.
    Once is_active is decoupled from verified_email, we will no longer need this
    class override.

    This class can be used for an OAuth2-accessible endpoint that allows users to access
    that endpoint without having their email verified.  For example, this is used
    for mobile endpoints.
    """

    allow_inactive_users = True


class OAuth2Authentication(BearerAuthentication):
    """
    Creating temperary class cause things outside of edx-platform need OAuth2Authentication.
    This will be removed when repos outside edx-platform import BearerAuthentiction instead.
    """


class OAuth2AuthenticationAllowInactiveUser(BearerAuthenticationAllowInactiveUser):
    """
    Creating temperary class cause things outside of edx-platform need OAuth2Authentication.
    This will be removed when repos outside edx-platform import BearerAuthentiction instead.
    """
