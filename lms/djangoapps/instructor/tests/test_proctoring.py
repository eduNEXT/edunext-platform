"""
Unit tests for Edx Proctoring feature flag in new instructor dashboard.
"""

from unittest.mock import patch

import ddt
from django.apps import apps
from django.conf import settings
from django.urls import reverse
from edx_proctoring.api import create_exam
from edx_proctoring.backends.tests.test_backend import TestBackendProvider

from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from common.djangoapps.student.tests.factories import AdminFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


@patch.dict(settings.FEATURES, {'ENABLE_SPECIAL_EXAMS': True})
@ddt.ddt
class TestProctoringDashboardViews(SharedModuleStoreTestCase):
    """
    Check for Proctoring view on the new instructor dashboard
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        button = '<button type="button" class="btn-link special_exams" data-section="special_exams">Special Exams</button>'  # lint-amnesty, pylint: disable=line-too-long
        cls.proctoring_link = button

    def setUp(self):
        super().setUp()

        # Create instructor account
        self.instructor = AdminFactory.create()
        self.client.login(username=self.instructor.username, password="test")

    def setup_course_url(self, course):
        """
        Create URL for instructor dashboard
        """
        self.url = reverse('instructor_dashboard', kwargs={'course_id': str(course.id)})  # lint-amnesty, pylint: disable=attribute-defined-outside-init

    def setup_course(self, enable_proctored_exams, enable_timed_exams):
        """
        Create course based on proctored exams and timed exams values
        """
        self.course = CourseFactory.create(enable_proctored_exams=enable_proctored_exams,  # lint-amnesty, pylint: disable=attribute-defined-outside-init
                                           enable_timed_exams=enable_timed_exams)
        self.setup_course_url(self.course)

    def setup_course_with_proctoring_backend(self, proctoring_provider, escalation_email):
        """
        Create course based on proctoring provider and escalation email values
        """
        course = CourseFactory.create(enable_proctored_exams=True,
                                      enable_timed_exams=True,
                                      proctoring_provider=proctoring_provider,
                                      proctoring_escalation_email=escalation_email)
        self.setup_course_url(course)

    @ddt.data(
        (True, False),
        (False, True)
    )
    @ddt.unpack
    def test_proctoring_tab_visible_for_global_staff(self, enable_proctored_exams, enable_timed_exams):
        """
        Test Proctoring Tab is visible in the Instructor Dashboard
        for global staff
        """
        self.setup_course(enable_proctored_exams, enable_timed_exams)

        self.instructor.is_staff = True
        self.instructor.save()

        # verify that proctoring tab is visible for global staff
        self._assert_proctoring_tab_available(True)

    @ddt.data(
        (True, False),
        (False, True)
    )
    @ddt.unpack
    def test_proctoring_tab_visible_for_course_staff_and_admin(self, enable_proctored_exams, enable_timed_exams):
        """
        Test Proctoring Tab is visible in the Instructor Dashboard
        for course staff(role of STAFF or ADMIN)
        """
        self.setup_course(enable_proctored_exams, enable_timed_exams)

        self.instructor.is_staff = False
        self.instructor.save()

        # verify that proctoring tab is visible for course staff
        CourseStaffRole(self.course.id).add_users(self.instructor)
        self._assert_proctoring_tab_available(True)

        # verify that proctoring tab is visible for course instructor
        CourseStaffRole(self.course.id).remove_users(self.instructor)
        CourseInstructorRole(self.course.id).add_users(self.instructor)
        self._assert_proctoring_tab_available(True)

    @ddt.data(
        (True, False),
        (False, True)
    )
    @ddt.unpack
    def test_no_proctoring_tab_non_global_staff(self, enable_proctored_exams, enable_timed_exams):
        """
        Test Proctoring Tab is not visible in the Instructor Dashboard
        for course team other than role of staff or admin
        """
        self.setup_course(enable_proctored_exams, enable_timed_exams)

        self.instructor.is_staff = False
        self.instructor.save()
        self._assert_proctoring_tab_available(False)

    @patch.dict(settings.FEATURES, {'ENABLE_SPECIAL_EXAMS': False})
    @ddt.data(
        (True, False),
        (False, True)
    )
    @ddt.unpack
    def test_no_tab_flag_unset(self, enable_proctored_exams, enable_timed_exams):
        """
        Special Exams tab will not be visible if special exams settings are not enabled inspite of
        proctored exams or timed exams is enabled
        """
        self.setup_course(enable_proctored_exams, enable_timed_exams)

        self.instructor.is_staff = True
        self.instructor.save()
        self._assert_proctoring_tab_available(False)

    @patch.dict(settings.PROCTORING_BACKENDS,
                {
                    'DEFAULT': 'test_proctoring_provider',
                    'test_proctoring_provider': {},
                    'proctortrack': {}
                },
                )
    @ddt.data(
        ('test_proctoring_provider', None),
        ('test_proctoring_provider', 'foo@bar.com')
    )
    @ddt.unpack
    def test_non_proctortrack_provider(self, proctoring_provider, escalation_email):
        """
        Escalation email will not be visible if proctortrack is not the proctoring provider, with or without
        escalation email provided.
        """
        self.setup_course_with_proctoring_backend(proctoring_provider, escalation_email)

        self.instructor.is_staff = True
        self.instructor.save()
        self._assert_escalation_email_available(False)

    @patch.dict(settings.PROCTORING_BACKENDS,
                {
                    'DEFAULT': 'test_proctoring_provider',
                    'test_proctoring_provider': {},
                    'proctortrack': {}
                },
                )
    def test_proctortrack_provider_with_email(self):
        """
        Escalation email will be visible if proctortrack is the proctoring provider, and there
        is an escalation email provided.
        """
        self.setup_course_with_proctoring_backend('proctortrack', 'foo@bar.com')

        self.instructor.is_staff = True
        self.instructor.save()
        self._assert_escalation_email_available(True)

    def test_review_dashboard(self):
        """
        The exam review dashboard will appear for backends that support the feature
        """
        self.setup_course(True, True)
        response = self.client.get(self.url)
        # the default backend does not support the review dashboard
        self.assertNotContains(response, 'Review Dashboard')

        backend = TestBackendProvider()
        config = apps.get_app_config('edx_proctoring')
        with patch.object(config, 'backends', {'test': backend}):
            create_exam(
                course_id=self.course.id,
                content_id='test_content',
                exam_name='Final Test Exam',
                time_limit_mins=10,
                backend='test',
            )
            response = self.client.get(self.url)
            self.assertContains(response, 'Review Dashboard')

    def _assert_proctoring_tab_available(self, available):
        """
        Asserts that proctoring tab is/is not available for logged in user.
        """
        func = self.assertIn if available else self.assertNotIn
        response = self.client.get(self.url)
        func(self.proctoring_link, response.content.decode('utf-8'))
        func('proctoring-wrapper', response.content.decode('utf-8'))

    def _assert_escalation_email_available(self, available):
        """
        Asserts that escalation email is/is not available for logged in user
        """
        func = self.assertIn if available else self.assertNotIn
        response = self.client.get(self.url)
        func('escalation-email-container', response.content.decode('utf-8'))
