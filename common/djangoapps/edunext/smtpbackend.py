"""
Microsite configuration email backend module.

Contains the class for microsite email backend.


"""

from django.core.mail.backends.smtp import EmailBackend
from openedx.conf import settings


class MicrositeAwareEmailBackend (EmailBackend):

    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):

        super(MicrositeEmailBackend, self).__init__()
        self.username = settings.EMAIL_HOST_USER
        self.password = settings.EMAIL_HOST_PASSWORD
