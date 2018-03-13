"""
Utility methods related to course
"""
import logging
import urllib

from openedx.conf import settings
from microsite_configuration import microsite

log = logging.getLogger(__name__)

COURSE_SHARING_UTM_PARAMETERS = {
    'facebook': {
        'utm_medium': 'social-post',
        'utm_campaign': 'social-sharing',
        'utm_source': 'facebook',
    },
    'twitter': {
        'utm_medium': 'social-post',
        'utm_campaign': 'social-sharing',
        'utm_source': 'twitter',
    },
}


def get_encoded_course_sharing_utm_params():
    """
    Returns encoded Course Sharing UTM Parameters.
    """
    return {
        utm_source: urllib.urlencode(utm_params)
        for utm_source, utm_params in COURSE_SHARING_UTM_PARAMETERS.iteritems()
    }


def get_link_for_about_page(course):
    """
    Arguments:
        course: This can be either a course overview object or a course descriptor.

    Returns the course sharing url, this can be one of course's social sharing url, marketing url, or
    lms course about url.
    """
    is_social_sharing_enabled = getattr(settings, 'SOCIAL_SHARING_SETTINGS', {}).get('CUSTOM_COURSE_URLS')
    if is_social_sharing_enabled and course.social_sharing_url:
        course_about_url = course.social_sharing_url
    elif settings.FEATURES.get('ENABLE_MKTG_SITE') and getattr(course, 'marketing_url', None):
        course_about_url = course.marketing_url
    else:
        # eduNEXT 23.12.2015 make the link microsite aware, based on the org of
        # the course
        about_base = microsite.get_value_for_org(
            course.id.org, 'SITE_NAME', settings.LMS_ROOT_URL)

        if not about_base.startswith("http"):
            about_base = u"{protocol}://{base}".format(
                protocol="https",
                base=about_base
            )

        course_about_url = u'{about_base_url}/courses/{course_key}/about'.format(
            about_base_url=about_base,
            course_key=unicode(course.id),
        )

    return course_about_url
