""" Overrides for Docker-based eduNEXT devstack. """

from .devstack_docker import *  # pylint: disable=wildcard-import, unused-wildcard-import


LOGGING['handlers']['tracking'] = {
    'level': 'DEBUG',
    'class': 'logging.FileHandler',
    'filename': '/edx/var/log/tracking/tracking.log',
    'formatter': 'raw',
    }

LOGGING['loggers']['tracking']['handlers'] = ['tracking']
