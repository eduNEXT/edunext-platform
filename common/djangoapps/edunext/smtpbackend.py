"""
Microsite configuration email backend module.

Contains the class for microsite email backend.


"""

from django.core.mail.backends.smtp import EmailBackend
from openedx.conf import settings
from microsite_configuration import microsite


class MicrositeAwareEmailBackend (EmailBackend):

    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):

        super(MicrositeAwareEmailBackend, self).__init__()
        self.username = settings.EMAIL_HOST_USER
        self.password = settings.EMAIL_HOST_PASSWORD

    def _send(self, email_message):
        """A custom helper method that sends email and adds mailgun tags """

        email_tag = microsite.get_value('microsite_config_key', 'eduNEXT')
        email_message.extra_headers['X-Mailgun-Tag'] = email_tag
        super(MicrositeAwareEmailBackend, self)._send(email_message)
