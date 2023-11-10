"""
Simple utility functions for computing access.
It allows us to share code between access.py and block transformers.
"""


from datetime import datetime, timedelta
from logging import getLogger

from django.conf import settings
from pytz import UTC
from lms.djangoapps.courseware.access_response import (
    AccessResponse,
    StartDateError,
    EnrollmentRequiredAccessError,
    AuthenticationRequiredAccessError,
)
from lms.djangoapps.courseware.masquerade import get_course_masquerade, is_masquerading_as_student
from openedx.core.djangoapps.util.user_messages import PageLevelMessages  # lint-amnesty, pylint: disable=unused-import
from openedx.core.djangolib.markup import HTML  # lint-amnesty, pylint: disable=unused-import
from openedx.features.course_experience import (
    COURSE_PRE_START_ACCESS_FLAG,
    COURSE_ENABLE_UNENROLLED_ACCESS_FLAG,
)
from common.djangoapps.student.models import CourseEnrollment
from common.djangoapps.student.roles import CourseBetaTesterRole
from xmodule.util.xmodule_django import get_current_request_hostname
from xmodule.course_module import COURSE_VISIBILITY_PUBLIC

DEBUG_ACCESS = False
log = getLogger(__name__)

ACCESS_GRANTED = AccessResponse(True)
ACCESS_DENIED = AccessResponse(False)


def debug(*args, **kwargs):
    """
    Helper function for local debugging.
    """
    # to avoid overly verbose output, this is off by default
    if DEBUG_ACCESS:
        log.debug(*args, **kwargs)


def adjust_start_date(user, days_early_for_beta, start, course_key):
    """
    If user is in a beta test group, adjust the start date by the appropriate number of
    days.

    Returns:
        A datetime.  Either the same as start, or earlier for beta testers.
    """
    if days_early_for_beta is None:
        # bail early if no beta testing is set up
        return start

    if CourseBetaTesterRole(course_key).has_user(user):
        debug("Adjust start time: user in beta role for %s", course_key)
        delta = timedelta(days_early_for_beta)
        effective = start - delta
        return effective

    return start


def check_start_date(user, days_early_for_beta, start, course_key, display_error_to_user=True, now=None):
    """
    Verifies whether the given user is allowed access given the
    start date and the Beta offset for the given course.

    Arguments:
        display_error_to_user: If True, display this error to users in the UI.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or StartDateError.
    """
    start_dates_disabled = settings.FEATURES.get('DISABLE_START_DATES', False)
    masquerading_as_student = is_masquerading_as_student(user, course_key)

    if start_dates_disabled and not masquerading_as_student:
        return ACCESS_GRANTED
    else:
        if start is None or in_preview_mode() or get_course_masquerade(user, course_key):
            return ACCESS_GRANTED

        if now is None:
            now = datetime.now(UTC)
        effective_start = adjust_start_date(user, days_early_for_beta, start, course_key)
        if now > effective_start:
            return ACCESS_GRANTED

        return StartDateError(start, display_error_to_user=display_error_to_user)


def in_preview_mode():
    """
    Returns whether the user is in preview mode or not.
    """
    hostname = get_current_request_hostname()
    preview_lms_base = settings.FEATURES.get('PREVIEW_LMS_BASE', None)
    return bool(preview_lms_base and hostname and hostname.split(':')[0] == preview_lms_base.split(':')[0])


def check_course_open_for_learner(user, course):
    """
    Check if the course is open for learners based on the start date.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or StartDateError.
    """
    if COURSE_PRE_START_ACCESS_FLAG.is_enabled():
        return ACCESS_GRANTED
    return check_start_date(user, course.days_early_for_beta, course.start, course.id)


def check_enrollment(user, course):
    """
    Check if the course requires a learner to be enrolled for access.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or EnrollmentRequiredAccessError.
    """
    if check_public_access(course, [COURSE_VISIBILITY_PUBLIC]):
        return ACCESS_GRANTED

    if CourseEnrollment.is_enrolled(user, course.id):
        return ACCESS_GRANTED

    return EnrollmentRequiredAccessError()


def check_authentication(user, course):
    """
    Grants access if the user is authenticated, or if the course allows public access.

    Returns:
        AccessResponse: Either ACCESS_GRANTED or AuthenticationRequiredAccessError
    """
    if user.is_authenticated:
        return ACCESS_GRANTED

    if check_public_access(course, [COURSE_VISIBILITY_PUBLIC]):
        return ACCESS_GRANTED

    return AuthenticationRequiredAccessError()


def check_public_access(course, visibilities):
    """
    This checks if the unenrolled access waffle flag for the course is set
    and the course visibility matches any of the input visibilities.

    The "visibilities" argument is one of these constants from xmodule.course_module:
    - COURSE_VISIBILITY_PRIVATE
    - COURSE_VISIBILITY_PUBLIC
    - COURSE_VISIBILITY_PUBLIC_OUTLINE

    Returns:
        AccessResponse: Either ACCESS_GRANTED or ACCESS_DENIED.
    """

    unenrolled_access_flag = COURSE_ENABLE_UNENROLLED_ACCESS_FLAG.is_enabled(course.id)
    allow_access = unenrolled_access_flag and course.course_visibility in visibilities
    if allow_access:
        return ACCESS_GRANTED

    return ACCESS_DENIED
