""" Overrides for Docker-based eduNEXT devstack. """

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=wildcard-import, unused-wildcard-import

from .devstack_docker import *


LOGGING['handlers']['tracking'] = {
    'level': 'DEBUG',
    'class': 'logging.FileHandler',
    'filename': '/edx/var/log/tracking/tracking.log',
    'formatter': 'raw',
}

LOGGING['loggers']['tracking']['handlers'] = ['tracking']
