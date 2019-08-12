"""
View logic for handling course welcome messages.
"""

from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import ensure_csrf_cookie
from opaque_keys.edx.keys import CourseKey
from web_fragments.fragment import Fragment

from course_updates import get_ordered_updates
from courseware.courses import get_course_with_access
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from openedx.core.djangoapps.user_api.course_tag.api import set_course_tag, get_course_tag

PREFERENCE_KEY = 'view-welcome-message'


class WelcomeMessageFragmentView(EdxFragmentView):
    """
    A fragment that displays a course's welcome message.
    """
    def render_to_fragment(self, request, course_id=None, **kwargs):
        """
        Renders the welcome message fragment for the specified course.

        Returns: A fragment, or None if there is no welcome message.
        """
        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
        welcome_message_html = self.welcome_message_html(request, course)
        if not welcome_message_html:
            return None

        dismiss_url = reverse(
            'openedx.course_experience.dismiss_welcome_message', kwargs={'course_id': unicode(course_key)}
        )

        latest_update_id = get_latest_update_id(request, course)

        context = {
            'dismiss_url': dismiss_url,
            'welcome_message_html': welcome_message_html,
            'welcome_message_id': latest_update_id
        }

        # If the course tag is the same as the latest update id then the message was dismissed
        if (get_course_tag(request.user, course_key, PREFERENCE_KEY) == latest_update_id or
                latest_update_id is None):
            return None
        else:
            # If the tag is different from the latest update, then there's a new update to show
            html = render_to_string('course_experience/welcome-message-fragment.html', context)
            return Fragment(html)

    @classmethod
    def welcome_message_html(cls, request, course):
        """
        Returns the course's welcome message or None if it doesn't have one.
        """
        # Return the course update with the most recent publish date
        ordered_updates = get_ordered_updates(request, course)
        content = None
        if ordered_updates:
            content = ordered_updates[0]['content']

        return content


@ensure_csrf_cookie
def dismiss_welcome_message(request, course_id):
    """
    Given the course_id in the request, disable displaying the welcome message for the user.
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, 'load', course_key, check_if_enrolled=True)
    latest_update_id = get_latest_update_id(request, course)
    # The course tag will be the id of the dissmised update.
    set_course_tag(request.user, course_key, PREFERENCE_KEY, latest_update_id)

    return HttpResponse()


def get_latest_update_id(request, course):
    """
    Returns the most recent update id or None if there are no updates.
    """
    ordered_updates = get_ordered_updates(request, course)
    latest_update_id = None
    if ordered_updates:
        latest_update_id = ordered_updates[0]['id']

    return str(latest_update_id)
