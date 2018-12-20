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

############################### LANG ########################

LANGUAGE_CODE = 'en'
TIME_ZONE = 'America/Bogota'
FEATURES['SHOW_HEADER_LANGUAGE_SELECTOR'] = True
FEATURES['SHOW_FOOTER_LANGUAGE_SELECTOR'] = True
FEATURES['EDNX_SITE_AWARE_LOCALE'] = True


################################ ASYNC WORKERS ################################

# Require a separate celery worker
CELERY_ALWAYS_EAGER = False

# Disable transaction management because we are using a worker. Views
# that request a task and wait for the result will deadlock otherwise.
for database_name in DATABASES:
    DATABASES[database_name]['ATOMIC_REQUESTS'] = False


CELERY_BROKER_HOSTNAME = "edx.devstack.rabbit"
CELERY_BROKER_VHOST = "devstack"
CELERY_BROKER_USER = "celery"
CELERY_BROKER_PASSWORD = "celery"

BROKER_URL = "{0}://{1}:{2}@{3}/{4}".format(CELERY_BROKER_TRANSPORT,
                                            CELERY_BROKER_USER,
                                            CELERY_BROKER_PASSWORD,
                                            CELERY_BROKER_HOSTNAME,
                                            CELERY_BROKER_VHOST)

GRADES_DOWNLOAD = {
    'STORAGE_TYPE': 'localfs',
    'BUCKET': 'openedx-grades',
    'ROOT_PATH': '/edx/var/edxapp/uploads',
}
