"""
This module is essentially a broker to xmodule/tabs.py -- it was originally introduced to
perform some LMS-specific tab display gymnastics for the Entrance Exams feature
"""


from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_noop

from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.courseware.entrance_exams import user_can_skip_entrance_exam
from lms.djangoapps.course_home_api.toggles import course_home_mfe_dates_tab_is_active, course_home_mfe_outline_tab_is_active, course_home_mfe_progress_tab_is_active  # lint-amnesty, pylint: disable=line-too-long
from openedx.core.lib.course_tabs import CourseTabPluginManager
from openedx.features.course_experience import DISABLE_UNIFIED_COURSE_TAB_FLAG, default_course_url_name
from openedx.features.course_experience.url_helpers import get_learning_mfe_home_url
from openedx.features.course_experience import RELATIVE_DATES_FLAG
from common.djangoapps.student.models import CourseEnrollment
from xmodule.tabs import CourseTab, CourseTabList, course_reverse_func_from_name_func, key_checker


class EnrolledTab(CourseTab):
    """
    A base class for any view types that require a user to be enrolled.
    """
    @classmethod
    def is_enabled(cls, course, user=None):
        return user and user.is_authenticated and \
            bool(CourseEnrollment.is_enrolled(user, course.id) or has_access(user, 'staff', course, course.id))


class CoursewareTab(EnrolledTab):
    """
    The main courseware view.
    """
    type = 'courseware'
    title = ugettext_noop('Course')
    priority = 10
    view_name = 'courseware'
    is_movable = False
    is_default = False
    supports_preview_menu = True

    def __init__(self, tab_dict):
        def link_func(course, reverse_func):
            if course_home_mfe_outline_tab_is_active(course.id):
                return get_learning_mfe_home_url(course_key=course.id, view_name='home')
            else:
                reverse_name_func = lambda course: default_course_url_name(course.id)
                url_func = course_reverse_func_from_name_func(reverse_name_func)
                return url_func(course, reverse_func)

        tab_dict['link_func'] = link_func
        super().__init__(tab_dict)

    @classmethod
    def is_enabled(cls, course, user=None):
        """
        Returns true if this tab is enabled.
        """
        if DISABLE_UNIFIED_COURSE_TAB_FLAG.is_enabled(course.id):
            return super().is_enabled(course, user)
        # If this is the unified course tab then it is always enabled
        return True


class CourseInfoTab(CourseTab):
    """
    The course info view.
    """
    type = 'course_info'
    title = ugettext_noop('Home')
    priority = 20
    view_name = 'info'
    tab_id = 'info'
    is_movable = False
    is_default = False

    @classmethod
    def is_enabled(cls, course, user=None):
        return True


class SyllabusTab(EnrolledTab):
    """
    A tab for the course syllabus.
    """
    type = 'syllabus'
    title = ugettext_noop('Syllabus')
    priority = 30
    view_name = 'syllabus'
    allow_multiple = True
    is_default = False

    @classmethod
    def is_enabled(cls, course, user=None):
        if not super().is_enabled(course, user=user):
            return False
        return getattr(course, 'syllabus_present', False)


class ProgressTab(EnrolledTab):
    """
    The course progress view.
    """
    type = 'progress'
    title = ugettext_noop('Progress')
    priority = 40
    view_name = 'progress'
    is_hideable = True
    is_default = False

    def __init__(self, tab_dict):
        def link_func(course, reverse_func):
            if course_home_mfe_progress_tab_is_active(course.id):
                return get_learning_mfe_home_url(course_key=course.id, view_name=self.view_name)
            else:
                return reverse_func(self.view_name, args=[str(course.id)])

        tab_dict['link_func'] = link_func
        super(ProgressTab, self).__init__(tab_dict)  # pylint: disable=super-with-arguments

    @classmethod
    def is_enabled(cls, course, user=None):
        if not super().is_enabled(course, user=user):
            return False
        return not course.hide_progress_tab


class TextbookTabsBase(CourseTab):
    """
    Abstract class for textbook collection tabs classes.
    """
    # Translators: 'Textbooks' refers to the tab in the course that leads to the course' textbooks
    title = ugettext_noop("Textbooks")
    is_collection = True
    is_default = False

    @classmethod
    def is_enabled(cls, course, user=None):
        return user is None or user.is_authenticated

    @classmethod
    def items(cls, course):
        """
        A generator for iterating through all the SingleTextbookTab book objects associated with this
        collection of textbooks.
        """
        raise NotImplementedError()


class TextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all textbook tabs.
    """
    type = 'textbooks'
    priority = None
    view_name = 'book'

    @classmethod
    def is_enabled(cls, course, user=None):
        parent_is_enabled = super().is_enabled(course, user)
        return settings.FEATURES.get('ENABLE_TEXTBOOK') and parent_is_enabled

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.textbooks):
            yield SingleTextbookTab(
                name=textbook.title,
                tab_id=f'textbook/{index}',
                view_name=cls.view_name,
                index=index
            )


class PDFTextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all PDF textbook tabs.
    """
    type = 'pdf_textbooks'
    priority = None
    view_name = 'pdf_book'

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.pdf_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id=f'pdftextbook/{index}',
                view_name=cls.view_name,
                index=index
            )


class HtmlTextbookTabs(TextbookTabsBase):
    """
    A tab representing the collection of all Html textbook tabs.
    """
    type = 'html_textbooks'
    priority = None
    view_name = 'html_book'

    @classmethod
    def items(cls, course):
        for index, textbook in enumerate(course.html_textbooks):
            yield SingleTextbookTab(
                name=textbook['tab_title'],
                tab_id=f'htmltextbook/{index}',
                view_name=cls.view_name,
                index=index
            )


class LinkTab(CourseTab):
    """
    Abstract class for tabs that contain external links.
    """
    link_value = ''

    def __init__(self, tab_dict=None, link=None):
        self.link_value = tab_dict['link'] if tab_dict else link

        def link_value_func(_course, _reverse_func):
            """ Returns the link_value as the link. """
            return self.link_value

        self.type = tab_dict['type']

        tab_dict['link_func'] = link_value_func

        super().__init__(tab_dict)

    def __getitem__(self, key):
        if key == 'link':
            return self.link_value
        else:
            return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key == 'link':
            self.link_value = value
        else:
            super().__setitem__(key, value)

    def to_json(self):
        to_json_val = super().to_json()
        to_json_val.update({'link': self.link_value})
        return to_json_val

    def __eq__(self, other):
        if not super().__eq__(other):
            return False
        return self.link_value == other.get('link')

    @classmethod
    def is_enabled(cls, course, user=None):
        return True


class ExternalDiscussionCourseTab(LinkTab):
    """
    A course tab that links to an external discussion service.
    """

    type = 'external_discussion'
    # Translators: 'Discussion' refers to the tab in the courseware that leads to the discussion forums
    title = ugettext_noop('Discussion')
    priority = None
    is_default = False

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        """ Validate that the tab_dict for this course tab has the necessary information to render. """
        return (super().validate(tab_dict, raise_error) and
                key_checker(['link'])(tab_dict, raise_error))

    @classmethod
    def is_enabled(cls, course, user=None):
        if not super().is_enabled(course, user=user):
            return False
        return course.discussion_link


class ExternalLinkCourseTab(LinkTab):
    """
    A course tab containing an external link.
    """
    type = 'external_link'
    priority = None
    is_default = False    # An external link tab is not added to a course by default
    allow_multiple = True

    @classmethod
    def validate(cls, tab_dict, raise_error=True):
        """ Validate that the tab_dict for this course tab has the necessary information to render. """
        return (super().validate(tab_dict, raise_error) and
                key_checker(['link', 'name'])(tab_dict, raise_error))


class SingleTextbookTab(CourseTab):
    """
    A tab representing a single textbook.  It is created temporarily when enumerating all textbooks within a
    Textbook collection tab.  It should not be serialized or persisted.
    """
    type = 'single_textbook'
    is_movable = False
    is_collection_item = True
    priority = None

    def __init__(self, name, tab_id, view_name, index):
        def link_func(course, reverse_func, index=index):
            """ Constructs a link for textbooks from a view name, a course, and an index. """
            return reverse_func(view_name, args=[str(course.id), index])

        tab_dict = dict()
        tab_dict['name'] = name
        tab_dict['tab_id'] = tab_id
        tab_dict['link_func'] = link_func
        super().__init__(tab_dict)

    def to_json(self):
        raise NotImplementedError('SingleTextbookTab should not be serialized.')


class DatesTab(EnrolledTab):
    """
    A tab representing the relevant dates for a course.
    """
    type = "dates"
    title = ugettext_noop(
        "Dates")  # We don't have the user in this context, so we don't want to translate it at this level.
    priority = 50
    view_name = "dates"
    is_dynamic = True

    def __init__(self, tab_dict):
        def link_func(course, reverse_func):
            if course_home_mfe_dates_tab_is_active(course.id):
                return get_learning_mfe_home_url(course_key=course.id, view_name=self.view_name)
            else:
                return reverse_func(self.view_name, args=[str(course.id)])

        tab_dict['link_func'] = link_func
        super().__init__(tab_dict)

    @classmethod
    def is_enabled(cls, course, user=None):
        """Returns true if this tab is enabled."""
        return RELATIVE_DATES_FLAG.is_enabled(course.id) and super(DatesTab, cls).is_enabled(course, user=user)


def get_course_tab_list(user, course):
    """
    Retrieves the course tab list from xmodule.tabs and manipulates the set as necessary
    """
    xmodule_tab_list = CourseTabList.iterate_displayable(course, user=user)

    # Now that we've loaded the tabs for this course, perform the Entrance Exam work.
    # If the user has to take an entrance exam, we'll need to hide away all but the
    # "Courseware" tab. The tab is then renamed as "Entrance Exam".
    course_tab_list = []
    must_complete_ee = not user_can_skip_entrance_exam(user, course)
    for tab in xmodule_tab_list:
        if must_complete_ee:
            # Hide all of the tabs except for 'Courseware'
            # Rename 'Courseware' tab to 'Entrance Exam'
            if tab.type != 'courseware':
                continue
            tab.name = _("Entrance Exam")
        # TODO: LEARNER-611 - once the course_info tab is removed, remove this code
        if not DISABLE_UNIFIED_COURSE_TAB_FLAG.is_enabled(course.id) and tab.type == 'course_info':
            continue
        if tab.type == 'static_tab' and tab.course_staff_only and \
                not bool(user and has_access(user, 'staff', course, course.id)):
            continue
        # We had initially created a CourseTab.load() for dates that ended up
        # persisting the dates tab tomodulestore on Course Run creation, but
        # ignoring any static dates tab here we can fix forward without
        # allowing the bug to continue to surface
        if tab.type == 'dates':
            continue
        course_tab_list.append(tab)

    # Add in any dynamic tabs, i.e. those that are not persisted
    course_tab_list += _get_dynamic_tabs(course, user)
    # Sorting here because although the CourseTabPluginManager.get_tab_types function
    # does do sorting on priority, we only use it for getting the dynamic tabs.
    # We can't switch this function to just use the CourseTabPluginManager without
    # further investigation since CourseTabList.iterate_displayable returns
    # Static Tabs that are not returned by the CourseTabPluginManager.
    course_tab_list.sort(key=lambda tab: tab.priority or float('inf'))
    return course_tab_list


def _get_dynamic_tabs(course, user):
    """
    Returns the dynamic tab types for the current user.

    Note: dynamic tabs are those that are not persisted in the course, but are
    instead added dynamically based upon the user's role.
    """
    dynamic_tabs = list()
    for tab_type in CourseTabPluginManager.get_tab_types():
        if getattr(tab_type, "is_dynamic", False):
            tab = tab_type(dict())
            if tab.is_enabled(course, user=user):
                dynamic_tabs.append(tab)
    dynamic_tabs.sort(key=lambda dynamic_tab: dynamic_tab.name)
    return dynamic_tabs
