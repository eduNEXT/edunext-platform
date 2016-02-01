import json
import time
import traceback

from base64 import b64decode

from django.conf import settings
from django.http import validate_host
from django.contrib.auth.models import User

from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header


def decode_token(data):
    missing_padding = 4 - len(data) % 4
    if missing_padding:
        data += b'=' * missing_padding
    data_base64ed = b64decode(data)
    return data_base64ed


def verify_sign(public_key, signature, data):
    '''
    Verifies with a public key from whom the data came that it was indeed
    signed by their private key
    param: public_key_loc Path to public key
    param: signature String signature to be verified
    return: Boolean. True if the signature is valid; False otherwise.
    '''
    from Crypto.PublicKey import RSA
    from Crypto.Signature import PKCS1_v1_5
    from Crypto.Hash import SHA256
    pub_key = public_key
    rsakey = RSA.importKey(pub_key)
    signer = PKCS1_v1_5.new(rsakey)
    digest = SHA256.new()
    digest.update(data)
    if signer.verify(digest, b64decode(signature)):
        return True
    return False


class MicrositeManagerAuthentication(authentication.BaseAuthentication):
    """
    Restrict the microsite api to requests with valid token from allowed hosts
    """

    def authenticate(self, request):
        try:
            # First validate the host
            self.validate_host(request)

            # Now on to the token
            auth = get_authorization_header(request).split()
            if not auth or auth[0].lower() != b'token':
                raise exceptions.AuthenticationFailed('Not allowed. Token required.')

            if len(auth) == 1:
                msg = 'Invalid token header. No credentials provided.'
                raise exceptions.AuthenticationFailed(msg)
            elif len(auth) > 2:
                msg = 'Invalid token header. Token string should not contain spaces.'
                raise exceptions.AuthenticationFailed(msg)

            return self.authenticate_credentials(auth[1])
        except exceptions.AuthenticationFailed, e:
            raise e
        except Exception:
            print traceback.format_exc()
            raise exceptions.AuthenticationFailed('Unknown Error. Check your logs.')

    def authenticate_credentials(self, key):
        """
        Validate an incoming token
        """
        try:
            d_msg = json.loads(decode_token(key))
        except TypeError:
            raise exceptions.AuthenticationFailed('Not allowed. Wrong token.')
        except ValueError:
            raise exceptions.AuthenticationFailed('Not allowed. No information.')

        verified = verify_sign(settings.MICROSITE_API_SIGNING_KEY, d_msg['signature'], d_msg['message'])
        if not verified:
            raise exceptions.AuthenticationFailed('Not allowed. Wrong signature.')

        d_message = json.loads(d_msg['message'])
        lived_for = time.time() - d_message['Time']
        if lived_for >= d_message['TTL']:
            raise exceptions.AuthenticationFailed('Not allowed. Token expired.')

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
