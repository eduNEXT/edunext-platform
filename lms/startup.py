"""
Module for code that should run during LMS startup
"""

# pylint: disable=unused-argument

from django.conf import settings

# Force settings to run so that the python path is modified
settings.INSTALLED_APPS  # pylint: disable=pointless-statement

from django_startup import autostartup
import edxmako
import logging
from monkey_patch import django_utils_translation
import analytics
from util import keyword_substitution
from microsite_configuration import microsite


log = logging.getLogger(__name__)


def run():
    """
    Executed during django startup
    """

    # Patch the xml libs.
    from safe_lxml import defuse_xml_libs
    defuse_xml_libs()

    django_utils_translation.patch()

    autostartup()

    add_mimetypes()

    if settings.FEATURES.get('USE_CUSTOM_THEME', False):
        enable_theme()

    if settings.FEATURES.get('USE_MICROSITES', False):
        microsite.enable_microsites(log)

    if settings.FEATURES.get('ENABLE_THIRD_PARTY_AUTH', False):
        enable_third_party_auth()

    # Initialize Segment.io analytics module. Flushes first time a message is received and
    # every 50 messages thereafter, or if 10 seconds have passed since last flush
    if settings.FEATURES.get('SEGMENT_IO_LMS') and hasattr(settings, 'SEGMENT_IO_LMS_KEY'):
        analytics.init(settings.SEGMENT_IO_LMS_KEY, flush_at=50)

    # Monkey patch the keyword function map
    if keyword_substitution.keyword_function_map_is_empty():
        keyword_substitution.add_keyword_function_map(get_keyword_function_map())
        # Once keyword function map is set, make update function do nothing
        keyword_substitution.add_keyword_function_map = lambda x: None


def add_mimetypes():
    """
    Add extra mimetypes. Used in xblock_resource.

    If you add a mimetype here, be sure to also add it in cms/startup.py.
    """
    import mimetypes

    mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
    mimetypes.add_type('application/x-font-opentype', '.otf')
    mimetypes.add_type('application/x-font-ttf', '.ttf')
    mimetypes.add_type('application/font-woff', '.woff')


def enable_theme():
    """
    Enable the settings for a custom theme, whose files should be stored
    in ENV_ROOT/themes/THEME_NAME (e.g., edx_all/themes/stanford).
    """
    # Workaround for setting THEME_NAME to an empty
    # string which is the default due to this ansible
    # bug: https://github.com/ansible/ansible/issues/4812
    if settings.THEME_NAME == "":
        settings.THEME_NAME = None
        return

    assert settings.FEATURES['USE_CUSTOM_THEME']
    settings.FAVICON_PATH = 'themes/{name}/images/favicon.ico'.format(
        name=settings.THEME_NAME
    )

    # Calculate the location of the theme's files
    theme_root = settings.ENV_ROOT / "themes" / settings.THEME_NAME

    # Include the theme's templates in the template search paths
    settings.TEMPLATE_DIRS.insert(0, theme_root / 'templates')
    edxmako.paths.add_lookup('main', theme_root / 'templates', prepend=True)

    # Namespace the theme's static files to 'themes/<theme_name>' to
    # avoid collisions with default edX static files
    settings.STATICFILES_DIRS.append(
        (u'themes/{}'.format(settings.THEME_NAME), theme_root / 'static')
    )

    # Include theme locale path for django translations lookup
    settings.LOCALE_PATHS = (theme_root / 'conf/locale',) + settings.LOCALE_PATHS


def enable_microsites():
    """
    Calls the enable_microsites function in the microsite backend.
    Here for backwards compatibility
    """
    microsite.enable_microsites(log)


def enable_third_party_auth():
    """
    Enable the use of third_party_auth, which allows users to sign in to edX
    using other identity providers. For configuration details, see
    common/djangoapps/third_party_auth/settings.py.
    """

    from third_party_auth import settings as auth_settings
    auth_settings.apply_settings(settings.THIRD_PARTY_AUTH, settings)


def get_keyword_function_map():
    """
    Define the mapping of keywords and filtering functions

    The functions are used to filter html, text and email strings
    before rendering them.

    The generated map will be monkey-patched onto the keyword_substitution
    module so that it persists along with the running server.

    Each function must take: user & course as parameters
    """

    from student.models import anonymous_id_for_user
    from util.date_utils import get_default_time_display

    def user_id_sub(user, course):
        """
        Gives the anonymous id for the given user

        For compatibility with the existing anon_ids, return anon_id without course_id
        """
        return anonymous_id_for_user(user, None)

    def user_fullname_sub(user, course=None):
        """ Returns the given user's name """
        return user.profile.name

    def course_display_name_sub(user, course):
        """ Returns the course's display name """
        return course.display_name

    def course_end_date_sub(user, course):
        """ Returns the course end date in the default display """
        return get_default_time_display(course.end)

    # Define keyword -> function map
    # Take care that none of these functions return %% encoded keywords
    kf_map = {
        '%%USER_ID%%': user_id_sub,
        '%%USER_FULLNAME%%': user_fullname_sub,
        '%%COURSE_DISPLAY_NAME%%': course_display_name_sub,
        '%%COURSE_END_DATE%%': course_end_date_sub
    }

    return kf_map
