"""
Specific overrides to the base prod settings to make development easier.
"""

from .aws import *  # pylint: disable=wildcard-import, unused-wildcard-import

# Don't use S3 in devstack, fall back to filesystem
del DEFAULT_FILE_STORAGE
MEDIA_ROOT = "/edx/var/edxapp/uploads"


DEBUG = True
USE_I18N = True
TEMPLATE_DEBUG = True
SITE_NAME = 'localhost:8000'
# By default don't use a worker, execute tasks as if they were local functions
CELERY_ALWAYS_EAGER = True

###############################LANG########################
LANGUAGE_CODE = 'es-419'
TIME_ZONE = 'America/Bogota'

################################ LOGGERS ######################################

import logging

# Disable noisy loggers
for pkg_name in ['track.contexts', 'track.middleware', 'dd.dogapi']:
    logging.getLogger(pkg_name).setLevel(logging.CRITICAL)


################################ EMAIL ########################################

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/edx/app/edxapp/edx-platform/email-messages'

FEATURES['ENABLE_INSTRUCTOR_EMAIL'] = True     # Enable email for all Studio courses
FEATURES['REQUIRE_COURSE_EMAIL_AUTH'] = False  # Give all courses email (don't require django-admin perms)
FEATURES['ENABLE_MULTIPART_EMAIL'] = True

########################## ANALYTICS TESTING ########################

ANALYTICS_SERVER_URL = "http://127.0.0.1:9000/"
ANALYTICS_API_KEY = ""

# Set this to the dashboard URL in order to display the link from the
# dashboard to the Analytics Dashboard.
ANALYTICS_DASHBOARD_URL = None


################################ DEBUG TOOLBAR ################################

INSTALLED_APPS += ('debug_toolbar', 'debug_toolbar_mongo')
MIDDLEWARE_CLASSES += ('django_comment_client.utils.QueryCountDebugMiddleware',
                       'debug_toolbar.middleware.DebugToolbarMiddleware',)
INTERNAL_IPS = ('127.0.0.1',)

DEBUG_TOOLBAR_PANELS = (
    # 'debug_toolbar.panels.version.VersionDebugPanel',
    # 'debug_toolbar.panels.timer.TimerDebugPanel',
    # 'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    # 'debug_toolbar.panels.headers.HeaderDebugPanel',
    # 'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    # 'debug_toolbar.panels.sql.SQLDebugPanel',
    # 'debug_toolbar.panels.signals.SignalDebugPanel',
    # 'debug_toolbar.panels.logger.LoggingPanel',
    # 'debug_toolbar_mongo.panel.MongoDebugPanel',

    #  Enabling the profiler has a weird bug as of django-debug-toolbar==0.9.4 and
    #  Django=1.3.1/1.4 where requests to views get duplicated (your method gets
    #  hit twice). So you can uncomment when you need to diagnose performance
    #  problems, but you shouldn't leave it on.
    #'debug_toolbar.panels.profiling.ProfilingDebugPanel',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': lambda _: True,
}

########################### PIPELINE #################################

PIPELINE_SASS_ARGUMENTS = '--debug-info --require {proj_dir}/static/sass/bourbon/lib/bourbon.rb'.format(proj_dir=PROJECT_ROOT)

########################### VERIFIED CERTIFICATES #################################

FEATURES['AUTOMATIC_VERIFY_STUDENT_IDENTITY_FOR_TESTING'] = True
FEATURES['ENABLE_PAYMENT_FAKE'] = True

CC_PROCESSOR_NAME = 'CyberSource2'
CC_PROCESSOR = {
    'CyberSource2': {
        "PURCHASE_ENDPOINT": '/shoppingcart/payment_fake/',
        "SECRET_KEY": 'abcd123',
        "ACCESS_KEY": 'abcd123',
        "PROFILE_ID": 'edx',
    }
}


########################### External REST APIs #################################
FEATURES['ENABLE_MOBILE_REST_API'] = True
FEATURES['ENABLE_VIDEO_ABSTRACTION_LAYER_API'] = True

########################## SECURITY #######################
FEATURES['ENFORCE_PASSWORD_POLICY'] = False
FEATURES['ENABLE_MAX_FAILED_LOGIN_ATTEMPTS'] = False
FEATURES['SQUELCH_PII_IN_LOGS'] = False
FEATURES['PREVENT_CONCURRENT_LOGINS'] = False
FEATURES['ADVANCED_SECURITY'] = False
PASSWORD_MIN_LENGTH = None
PASSWORD_COMPLEXITY = {}


########################### Milestones #################################
FEATURES['MILESTONES_APP'] = True


########################### Entrance Exams #################################
FEATURES['ENTRANCE_EXAMS'] = True


########################### MICROSITES #################################

MICROSITE_CONFIGURATION = {
    "devsite": {
        "domain_prefix": "devsite",
        "university": "devsite",
        "platform_name": "Development microsite",
        "logo_image_url": "devsite/images/header-logo.png",
        "email_from_address": "devsite@edunext.co",
        "payment_support_email": "devsite@edunext.co",
        "ENABLE_MKTG_SITE": False,
        "SITE_NAME": "devsite.devstack",
        "course_org_filter": "DevX",
        "course_about_show_social_links": False,
        "css_overrides_file": "devsite/css/microsite.css",
        "show_partners": False,
        "show_homepage_promo_video": False,
        "course_index_overlay_text": "",
        "course_index_overlay_logo_file": "devsite/images/header-logo.png",
        "homepage_overlay_html": ""
    },
    "devmktg": {
        "domain_prefix": "devmktg",
        "university": "devmktg",
        "platform_name": "Development microsite",
        "logo_image_url": "devmktg/images/header-logo.png",
        "email_from_address": "devmktg@edunext.co",
        "payment_support_email": "devmktg@edunext.co",
        "SITE_NAME": "devmktg.devstack",
        "course_org_filter": "DevX",
        "course_about_show_social_links": False,
        "css_overrides_file": "devmktg/css/microsite.css",
        "show_partners": False,
        "show_homepage_promo_video": False,
        "course_index_overlay_text": "",
        "course_index_overlay_logo_file": "devmktg/images/header-logo.png",
        "homepage_overlay_html": "",
        "ENABLE_MKTG_SITE": True,
        "MKTG_URLS": {
            'ABOUT': '/about-us',
            'CONTACT': '/contact-us',
            'FAQ': '/student-faq',
            'COURSES': '/courses',
            'ROOT': 'http://www.edunext.co',
            'TOS': '/edx-terms-service',
            'HONOR': '/terms',
            'PRIVACY': '/edx-privacy-policy',
            'WHAT_IS_VERIFIED_CERT': '/verified-certificate',
        }
    },
}

MICROSITE_ROOT_DIR = ENV_ROOT / 'microsites'
FEATURES['USE_MICROSITES'] = True


#####################################################################
# See if the developer has any local overrides.
try:
    from .private import *      # pylint: disable=import-error
except ImportError:
    pass

#####################################################################
# Lastly, run any migrations, if needed.
MODULESTORE = convert_module_store_setting_if_needed(MODULESTORE)
