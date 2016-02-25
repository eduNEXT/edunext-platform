"""Models for the util app. """
import cStringIO
import gzip
import logging

from django.db import models
from django.utils.text import compress_string

from config_models.models import ConfigurationModel

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class RateLimitConfiguration(ConfigurationModel):

    domain = models.CharField(
        max_length=255,
        default='default',
        help_text=ugettext_lazy(u"")
    )



