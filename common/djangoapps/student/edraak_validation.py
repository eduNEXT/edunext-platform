"""
Allow Unicode in Admin and LMS.
"""
import re
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


UNICODE_USERNAME_RE = re.compile(ur'^[\w._+-]+$', re.UNICODE)

VALIDATE_USERNAME = RegexValidator(
    UNICODE_USERNAME_RE,
    _("Enter a valid 'username' consisting of letters, numbers, underscores or hyphens."),
    'invalid'
)
