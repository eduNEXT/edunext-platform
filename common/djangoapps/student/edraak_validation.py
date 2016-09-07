"""
Allow Unicode in Admin and LMS.
"""
import re
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


unicode_username_re = re.compile(ur'^[\w._+-]+$', re.UNICODE)

validate_username = RegexValidator(
    unicode_username_re,
    _("Enter a valid 'username' consisting of letters, numbers, underscores or hyphens."),
    'invalid'
)
