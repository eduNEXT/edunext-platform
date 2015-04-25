from django.conf import settings
from django.http import validate_host
from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header


class MicrositeManagerAuthentication(authentication.BaseAuthentication):
    """
    Restrict the microsite api to requests with valid token from allowed hosts
    """

    def authenticate(self, request):
        # First validate the host
        self.validate_host(request)

        # Now on to the token
        auth = get_authorization_header(request).split()
        print auth
        if not auth or auth[0].lower() != b'token':
            raise exceptions.AuthenticationFailed('Not allowed. Token required.')

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(auth[1])

    def authenticate_credentials(self, key):
        # TODO: since the message goes over http, we have to sign the secret using a secure key
        if key != settings.MICROSITE_API_SECRET:
            raise exceptions.AuthenticationFailed('Not allowed')

        return self.get_management_user()

    def get_management_user(self):
        try:
            user = User.objects.get(username=settings.MICROSITE_API_MANAGER)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')
        return (user, None)

    def validate_host(self, request):
        """
        Only accept requests from known hosts
        """
        # TODO: must check how easy would be to spoof this
        if not validate_host(request.META.get('REMOTE_ADDR'), settings.MICROSITE_API_ALLOWED_REMOTES):
            raise exceptions.AuthenticationFailed('Host not allowed')
