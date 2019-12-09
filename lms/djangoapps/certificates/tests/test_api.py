"""Tests for the certificates Python API. """
import uuid
from contextlib import contextmanager
from functools import wraps

import ddt
from datetime import datetime
from datetime import timedelta
from config_models.models import cache
from django.conf import settings
from django.urls import reverse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.utils import timezone
from freezegun import freeze_time
from mock import patch
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import CourseLocator
import pytz

from course_modes.models import CourseMode
from course_modes.tests.factories import CourseModeFactory
from courseware.tests.factories import GlobalStaffFactory
from lms.djangoapps.certificates import api as certs_api
from lms.djangoapps.certificates.models import (
    CertificateGenerationConfiguration,
    CertificateStatuses,
    ExampleCertificate,
    GeneratedCertificate,
    certificate_status_for_student
)
from lms.djangoapps.certificates.queue import XQueueAddToQueueError, XQueueCertInterface
from lms.djangoapps.certificates.tests.factories import CertificateInvalidationFactory, GeneratedCertificateFactory
from lms.djangoapps.grades.tests.utils import mock_passing_grade
from openedx.core.djangoapps.site_configuration.tests.test_util import with_site_configuration
from openedx.core.lib.tests import attr
from student.models import CourseEnrollment
from student.tests.factories import UserFactory
from util.testing import EventTestMixin
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

FEATURES_WITH_CERTS_ENABLED = settings.FEATURES.copy()
FEATURES_WITH_CERTS_ENABLED['CERTIFICATES_HTML_VIEW'] = True


class WebCertificateTestMixin(object):
    """
    Mixin with helpers for testing Web Certificates.
    """
    @contextmanager
    def _mock_queue(self, is_successful=True):
        """
        Mock the "send to XQueue" method to return either success or an error.
        """
        symbol = 'capa.xqueue_interface.XQueueInterface.send_to_queue'
        with patch(symbol) as mock_send_to_queue:
            if is_successful:
                mock_send_to_queue.return_value = (0, "Successfully queued")
            else:
                mock_send_to_queue.side_effect = XQueueAddToQueueError(1, self.ERROR_REASON)

            yield mock_send_to_queue

    def _setup_course_certificate(self):
        """
        Creates certificate configuration for course
        """
        certificates = [
            {
                'id': 1,
                'name': 'Test Certificate Name',
                'description': 'Test Certificate Description',
                'course_title': 'tes_course_title',
                'signatories': [],
                'version': 1,
                'is_active': True
            }
        ]
        self.course.certificates = {'certificates': certificates}
        self.course.cert_html_view_enabled = True
        self.course.save()
        self.store.update_item(self.course, self.user.id)


@attr(shard=1)
@ddt.ddt
class CertificateDownloadableStatusTests(WebCertificateTestMixin, ModuleStoreTestCase):
    """Tests for the `certificate_downloadable_status` helper function. """
    ENABLED_SIGNALS = ['course_published']

    def setUp(self):
        super(CertificateDownloadableStatusTests, self).setUp()

        self.student = UserFactory()
        self.student_no_cert = UserFactory()
        self.course = CourseFactory.create(
            org='edx',
            number='verified',
            display_name='Verified Course',
            end=datetime.now(pytz.UTC),
            self_paced=False,
            certificate_available_date=datetime.now(pytz.UTC) - timedelta(days=2)
        )

        self.request_factory = RequestFactory()

    def test_cert_status_with_generating(self):
        GeneratedCertificateFactory.create(
            user=self.student,
            course_id=self.course.id,
            status=CertificateStatuses.generating,
            mode='verified'
        )
        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student, self.course.id),
            {
                'is_downloadable': False,
                'is_generating': True,
                'is_unverified': False,
                'download_url': None,
                'uuid': None,
            }
        )

    def test_cert_status_with_error(self):
        GeneratedCertificateFactory.create(
            user=self.student,
            course_id=self.course.id,
            status=CertificateStatuses.error,
            mode='verified'
        )

        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student, self.course.id),
            {
                'is_downloadable': False,
                'is_generating': True,
                'is_unverified': False,
                'download_url': None,
                'uuid': None
            }
        )

    def test_without_cert(self):
        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student_no_cert, self.course.id),
            {
                'is_downloadable': False,
                'is_generating': False,
                'is_unverified': False,
                'download_url': None,
                'uuid': None,
            }
        )

    def verify_downloadable_pdf_cert(self):
        """
        Verifies certificate_downloadable_status returns the
        correct response for PDF certificates.
        """
        cert = GeneratedCertificateFactory.create(
            user=self.student,
            course_id=self.course.id,
            status=CertificateStatuses.downloadable,
            mode='verified',
            download_url='www.google.com',
        )

        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student, self.course.id),
            {
                'is_downloadable': True,
                'is_generating': False,
                'is_unverified': False,
                'download_url': 'www.google.com',
                'uuid': cert.verify_uuid
            }
        )

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_pdf_cert_with_html_enabled(self):
        self.verify_downloadable_pdf_cert()

    def test_pdf_cert_with_html_disabled(self):
        self.verify_downloadable_pdf_cert()

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_with_downloadable_web_cert(self):
        CourseEnrollment.enroll(self.student, self.course.id, mode='honor')
        self._setup_course_certificate()
        with mock_passing_grade():
            certs_api.generate_user_certificates(self.student, self.course.id)

        cert_status = certificate_status_for_student(self.student, self.course.id)
        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student, self.course.id),
            {
                'is_downloadable': True,
                'is_generating': False,
                'is_unverified': False,
                'download_url': '/certificates/user/{user_id}/course/{course_id}'.format(
                    user_id=self.student.id,
                    course_id=self.course.id,
                ),
                'uuid': cert_status['uuid']
            }
        )

    @ddt.data(
        (False, timedelta(days=2), False),
        (False, -timedelta(days=2), True),
        (True, timedelta(days=2), True)
    )
    @ddt.unpack
    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_cert_api_return(self, self_paced, cert_avail_delta, cert_downloadable_status):
        """
        Test 'downloadable status'
        """
        cert_avail_date = datetime.now(pytz.UTC) + cert_avail_delta
        self.course.self_paced = self_paced
        self.course.certificate_available_date = cert_avail_date
        self.course.save()

        CourseEnrollment.enroll(self.student, self.course.id, mode='honor')
        self._setup_course_certificate()
        with mock_passing_grade():
            certs_api.generate_user_certificates(self.student, self.course.id)

        self.assertEqual(
            certs_api.certificate_downloadable_status(self.student, self.course.id)['is_downloadable'],
            cert_downloadable_status
        )


@attr(shard=1)
@ddt.ddt
class CertificateisInvalid(WebCertificateTestMixin, ModuleStoreTestCase):
    """Tests for the `is_certificate_invalid` helper function. """

    def setUp(self):
        super(CertificateisInvalid, self).setUp()

        self.student = UserFactory()
        self.course = CourseFactory.create(
            org='edx',
            number='verified',
            display_name='Verified Course'
        )
        self.global_staff = GlobalStaffFactory()
        self.request_factory = RequestFactory()

    def test_method_with_no_certificate(self):
        """ Test the case when there is no certificate for a user for a specific course. """
        course = CourseFactory.create(
            org='edx',
            number='honor',
            display_name='Course 1'
        )
        # Also check query count for 'is_certificate_invalid' method.
        with self.assertNumQueries(1):
            self.assertFalse(
                certs_api.is_certificate_invalid(self.student, course.id)
            )

    @ddt.data(
        CertificateStatuses.generating,
        CertificateStatuses.downloadable,
        CertificateStatuses.notpassing,
        CertificateStatuses.error,
        CertificateStatuses.unverified,
        CertificateStatuses.deleted,
        CertificateStatuses.unavailable,
    )
    def test_method_with_invalidated_cert(self, status):
        """ Verify that if certificate is marked as invalid than method will return
        True. """
        generated_cert = self._generate_cert(status)
        self._invalidate_certificate(generated_cert, True)
        self.assertTrue(
            certs_api.is_certificate_invalid(self.student, self.course.id)
        )

    @ddt.data(
        CertificateStatuses.generating,
        CertificateStatuses.downloadable,
        CertificateStatuses.notpassing,
        CertificateStatuses.error,
        CertificateStatuses.unverified,
        CertificateStatuses.deleted,
        CertificateStatuses.unavailable,
    )
    def test_method_with_inactive_invalidated_cert(self, status):
        """ Verify that if certificate is valid but it's invalidated status is
        false than method will return false. """
        generated_cert = self._generate_cert(status)
        self._invalidate_certificate(generated_cert, False)
        self.assertFalse(
            certs_api.is_certificate_invalid(self.student, self.course.id)
        )

    @ddt.data(
        CertificateStatuses.generating,
        CertificateStatuses.downloadable,
        CertificateStatuses.notpassing,
        CertificateStatuses.error,
        CertificateStatuses.unverified,
        CertificateStatuses.deleted,
        CertificateStatuses.unavailable,
    )
    def test_method_with_all_statues(self, status):
        """ Verify method return True if certificate has valid status but it is
        marked as invalid in CertificateInvalidation table. """

        certificate = self._generate_cert(status)
        CertificateInvalidationFactory.create(
            generated_certificate=certificate,
            invalidated_by=self.global_staff,
            active=True
        )
        # Also check query count for 'is_certificate_invalid' method.
        with self.assertNumQueries(2):
            self.assertTrue(
                certs_api.is_certificate_invalid(self.student, self.course.id)
            )

    def _invalidate_certificate(self, certificate, active):
        """ Dry method to mark certificate as invalid. """
        CertificateInvalidationFactory.create(
            generated_certificate=certificate,
            invalidated_by=self.global_staff,
            active=active
        )
        # Invalidate user certificate
        certificate.invalidate()
        self.assertFalse(certificate.is_valid())

    def _generate_cert(self, status):
        """ Dry method to generate certificate. """
        return GeneratedCertificateFactory.create(
            user=self.student,
            course_id=self.course.id,
            status=status,
            mode='verified'
        )


@attr(shard=1)
class CertificateGetTests(SharedModuleStoreTestCase):
    """Tests for the `test_get_certificate_for_user` helper function. """
    now = timezone.now()

    @classmethod
    def setUpClass(cls):
        cls.freezer = freeze_time(cls.now)
        cls.freezer.start()

        super(CertificateGetTests, cls).setUpClass()
        cls.student = UserFactory()
        cls.student_no_cert = UserFactory()
        cls.uuid = uuid.uuid4().hex
        cls.nonexistent_course_id = CourseKey.from_string('course-v1:some+fake+course')
        cls.web_cert_course = CourseFactory.create(
            org='edx',
            number='verified_1',
            display_name='Verified Course 1',
            cert_html_view_enabled=True
        )
        cls.pdf_cert_course = CourseFactory.create(
            org='edx',
            number='verified_2',
            display_name='Verified Course 2',
            cert_html_view_enabled=False
        )
        # certificate for the first course
        GeneratedCertificateFactory.create(
            user=cls.student,
            course_id=cls.web_cert_course.id,
            status=CertificateStatuses.downloadable,
            mode='verified',
            download_url='www.google.com',
            grade="0.88",
            verify_uuid=cls.uuid,
        )
        # certificate for the second course
        GeneratedCertificateFactory.create(
            user=cls.student,
            course_id=cls.pdf_cert_course.id,
            status=CertificateStatuses.downloadable,
            mode='honor',
            download_url='www.gmail.com',
            grade="0.99",
            verify_uuid=cls.uuid,
        )
        # certificate for a course that will be deleted
        GeneratedCertificateFactory.create(
            user=cls.student,
            course_id=cls.nonexistent_course_id,
            status=CertificateStatuses.downloadable
        )

    @classmethod
    def tearDownClass(cls):
        super(CertificateGetTests, cls).tearDownClass()
        cls.freezer.stop()

    def test_get_certificate_for_user(self):
        """
        Test to get a certificate for a user for a specific course.
        """
        cert = certs_api.get_certificate_for_user(self.student.username, self.web_cert_course.id)

        self.assertEqual(cert['username'], self.student.username)
        self.assertEqual(cert['course_key'], self.web_cert_course.id)
        self.assertEqual(cert['created'], self.now)
        self.assertEqual(cert['type'], CourseMode.VERIFIED)
        self.assertEqual(cert['status'], CertificateStatuses.downloadable)
        self.assertEqual(cert['grade'], "0.88")
        self.assertEqual(cert['is_passing'], True)
        self.assertEqual(cert['download_url'], 'www.google.com')

    def test_get_certificates_for_user(self):
        """
        Test to get all the certificates for a user
        """
        certs = certs_api.get_certificates_for_user(self.student.username)
        self.assertEqual(len(certs), 2)
        self.assertEqual(certs[0]['username'], self.student.username)
        self.assertEqual(certs[1]['username'], self.student.username)
        self.assertEqual(certs[0]['course_key'], self.web_cert_course.id)
        self.assertEqual(certs[1]['course_key'], self.pdf_cert_course.id)
        self.assertEqual(certs[0]['created'], self.now)
        self.assertEqual(certs[1]['created'], self.now)
        self.assertEqual(certs[0]['type'], CourseMode.VERIFIED)
        self.assertEqual(certs[1]['type'], CourseMode.HONOR)
        self.assertEqual(certs[0]['status'], CertificateStatuses.downloadable)
        self.assertEqual(certs[1]['status'], CertificateStatuses.downloadable)
        self.assertEqual(certs[0]['is_passing'], True)
        self.assertEqual(certs[1]['is_passing'], True)
        self.assertEqual(certs[0]['grade'], '0.88')
        self.assertEqual(certs[1]['grade'], '0.99')
        self.assertEqual(certs[0]['download_url'], 'www.google.com')
        self.assertEqual(certs[1]['download_url'], 'www.gmail.com')

    def test_no_certificate_for_user(self):
        """
        Test the case when there is no certificate for a user for a specific course.
        """
        self.assertIsNone(
            certs_api.get_certificate_for_user(self.student_no_cert.username, self.web_cert_course.id)
        )

    def test_no_certificates_for_user(self):
        """
        Test the case when there are no certificates for a user.
        """
        self.assertEqual(
            certs_api.get_certificates_for_user(self.student_no_cert.username),
            []
        )

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_get_web_certificate_url(self):
        """
        Test the get_certificate_url with a web cert course
        """
        expected_url = reverse(
            'certificates:render_cert_by_uuid',
            kwargs=dict(certificate_uuid=self.uuid)
        )
        cert_url = certs_api.get_certificate_url(
            user_id=self.student.id,
            course_id=self.web_cert_course.id,
            uuid=self.uuid
        )
        self.assertEqual(expected_url, cert_url)

        expected_url = reverse(
            'certificates:html_view',
            kwargs={
                "user_id": str(self.student.id),
                "course_id": unicode(self.web_cert_course.id),
            }
        )

        cert_url = certs_api.get_certificate_url(
            user_id=self.student.id,
            course_id=self.web_cert_course.id
        )
        self.assertEqual(expected_url, cert_url)

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_get_pdf_certificate_url(self):
        """
        Test the get_certificate_url with a pdf cert course
        """
        cert_url = certs_api.get_certificate_url(
            user_id=self.student.id,
            course_id=self.pdf_cert_course.id,
            uuid=self.uuid
        )
        self.assertEqual('www.gmail.com', cert_url)

    def test_get_certificate_with_deleted_course(self):
        """
        Test the case when there is a certificate but the course was deleted.
        """
        self.assertIsNone(
            certs_api.get_certificate_for_user(
                self.student.username,
                self.nonexistent_course_id
            )
        )


@attr(shard=1)
@override_settings(CERT_QUEUE='certificates')
class GenerateUserCertificatesTest(EventTestMixin, WebCertificateTestMixin, ModuleStoreTestCase):
    """Tests for generating certificates for students. """

    ERROR_REASON = "Kaboom!"
    ENABLED_SIGNALS = ['course_published']

    def setUp(self):  # pylint: disable=arguments-differ
        super(GenerateUserCertificatesTest, self).setUp('lms.djangoapps.certificates.api.tracker')

        self.student = UserFactory.create(
            email='joe_user@edx.org',
            username='joeuser',
            password='foo'
        )
        self.student_no_cert = UserFactory()
        self.course = CourseFactory.create(
            org='edx',
            number='verified',
            display_name='Verified Course',
            grade_cutoffs={'cutoff': 0.75, 'Pass': 0.5}
        )
        self.enrollment = CourseEnrollment.enroll(self.student, self.course.id, mode='honor')
        self.request_factory = RequestFactory()

    def test_new_cert_requests_into_xqueue_returns_generating(self):
        with mock_passing_grade():
            with self._mock_queue():
                certs_api.generate_user_certificates(self.student, self.course.id)

        # Verify that the certificate has status 'generating'
        cert = GeneratedCertificate.eligible_certificates.get(user=self.student, course_id=self.course.id)
        self.assertEqual(cert.status, CertificateStatuses.generating)
        self.assert_event_emitted(
            'edx.certificate.created',
            user_id=self.student.id,
            course_id=unicode(self.course.id),
            certificate_url=certs_api.get_certificate_url(self.student.id, self.course.id),
            certificate_id=cert.verify_uuid,
            enrollment_mode=cert.mode,
            generation_mode='batch'
        )

    def test_xqueue_submit_task_error(self):
        with mock_passing_grade():
            with self._mock_queue(is_successful=False):
                certs_api.generate_user_certificates(self.student, self.course.id)

        # Verify that the certificate has been marked with status error
        cert = GeneratedCertificate.eligible_certificates.get(user=self.student, course_id=self.course.id)
        self.assertEqual(cert.status, 'error')
        self.assertIn(self.ERROR_REASON, cert.error_reason)

    def test_generate_user_certificates_with_unverified_cert_status(self):
        """
        Generate user certificate when the certificate is unverified
        will trigger an update to the certificate if the user has since
        verified.
        """
        self._setup_course_certificate()
        # generate certificate with unverified status.
        GeneratedCertificateFactory.create(
            user=self.student,
            course_id=self.course.id,
            status=CertificateStatuses.unverified,
            mode='verified'
        )

        with mock_passing_grade():
            with self._mock_queue():
                status = certs_api.generate_user_certificates(self.student, self.course.id)
                self.assertEqual(status, 'generating')

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': True})
    def test_new_cert_requests_returns_generating_for_html_certificate(self):
        """
        Test no message sent to Xqueue if HTML certificate view is enabled
        """
        self._setup_course_certificate()
        with mock_passing_grade():
            certs_api.generate_user_certificates(self.student, self.course.id)

        # Verify that the certificate has status 'downloadable'
        cert = GeneratedCertificate.eligible_certificates.get(user=self.student, course_id=self.course.id)
        self.assertEqual(cert.status, CertificateStatuses.downloadable)

    @patch.dict(settings.FEATURES, {'CERTIFICATES_HTML_VIEW': False})
    def test_cert_url_empty_with_invalid_certificate(self):
        """
        Test certificate url is empty if html view is not enabled and certificate is not yet generated
        """
        url = certs_api.get_certificate_url(self.student.id, self.course.id)
        self.assertEqual(url, "")


@attr(shard=1)
@ddt.ddt
class CertificateGenerationEnabledTest(EventTestMixin, TestCase):
    """Test enabling/disabling self-generated certificates for a course. """

    COURSE_KEY = CourseLocator(org='test', course='test', run='test')

    def setUp(self):  # pylint: disable=arguments-differ
        super(CertificateGenerationEnabledTest, self).setUp('lms.djangoapps.certificates.api.tracker')

        # Since model-based configuration is cached, we need
        # to clear the cache before each test.
        cache.clear()

    @ddt.data(
        (None, None, False),
        (False, None, False),
        (False, True, False),
        (True, None, False),
        (True, False, False),
        (True, True, True)
    )
    @ddt.unpack
    def test_cert_generation_enabled(self, is_feature_enabled, is_course_enabled, expect_enabled):
        if is_feature_enabled is not None:
            CertificateGenerationConfiguration.objects.create(enabled=is_feature_enabled)

        if is_course_enabled is not None:
            certs_api.set_cert_generation_enabled(self.COURSE_KEY, is_course_enabled)
            cert_event_type = 'enabled' if is_course_enabled else 'disabled'
            event_name = '.'.join(['edx', 'certificate', 'generation', cert_event_type])
            self.assert_event_emitted(
                event_name,
                course_id=unicode(self.COURSE_KEY),
            )

        self._assert_enabled_for_course(self.COURSE_KEY, expect_enabled)

    def test_latest_setting_used(self):
        # Enable the feature
        CertificateGenerationConfiguration.objects.create(enabled=True)

        # Enable for the course
        certs_api.set_cert_generation_enabled(self.COURSE_KEY, True)
        self._assert_enabled_for_course(self.COURSE_KEY, True)

        # Disable for the course
        certs_api.set_cert_generation_enabled(self.COURSE_KEY, False)
        self._assert_enabled_for_course(self.COURSE_KEY, False)

    def test_setting_is_course_specific(self):
        # Enable the feature
        CertificateGenerationConfiguration.objects.create(enabled=True)

        # Enable for one course
        certs_api.set_cert_generation_enabled(self.COURSE_KEY, True)
        self._assert_enabled_for_course(self.COURSE_KEY, True)

        # Should be disabled for another course
        other_course = CourseLocator(org='other', course='other', run='other')
        self._assert_enabled_for_course(other_course, False)

    def _assert_enabled_for_course(self, course_key, expect_enabled):
        """Check that self-generated certificates are enabled or disabled for the course. """
        actual_enabled = certs_api.cert_generation_enabled(course_key)
        self.assertEqual(expect_enabled, actual_enabled)


@attr(shard=1)
class GenerateExampleCertificatesTest(TestCase):
    """Test generation of example certificates. """

    COURSE_KEY = CourseLocator(org='test', course='test', run='test')

    def test_generate_example_certs(self):
        # Generate certificates for the course
        CourseModeFactory.create(course_id=self.COURSE_KEY, mode_slug=CourseMode.HONOR)
        with self._mock_xqueue() as mock_queue:
            certs_api.generate_example_certificates(self.COURSE_KEY)

        # Verify that the appropriate certs were added to the queue
        self._assert_certs_in_queue(mock_queue, 1)

        # Verify that the certificate status is "started"
        self._assert_cert_status({
            'description': 'honor',
            'status': 'started'
        })

    def test_generate_example_certs_with_verified_mode(self):
        # Create verified and honor modes for the course
        CourseModeFactory.create(course_id=self.COURSE_KEY, mode_slug='honor')
        CourseModeFactory.create(course_id=self.COURSE_KEY, mode_slug='verified')

        # Generate certificates for the course
        with self._mock_xqueue() as mock_queue:
            certs_api.generate_example_certificates(self.COURSE_KEY)

        # Verify that the appropriate certs were added to the queue
        self._assert_certs_in_queue(mock_queue, 2)

        # Verify that the certificate status is "started"
        self._assert_cert_status(
            {
                'description': 'verified',
                'status': 'started'
            },
            {
                'description': 'honor',
                'status': 'started'
            }
        )

    @contextmanager
    def _mock_xqueue(self):
        """Mock the XQueue method for adding a task to the queue. """
        with patch.object(XQueueCertInterface, 'add_example_cert') as mock_queue:
            yield mock_queue

    def _assert_certs_in_queue(self, mock_queue, expected_num):
        """Check that the certificate generation task was added to the queue. """
        certs_in_queue = [call_args[0] for (call_args, __) in mock_queue.call_args_list]
        self.assertEqual(len(certs_in_queue), expected_num)
        for cert in certs_in_queue:
            self.assertTrue(isinstance(cert, ExampleCertificate))

    def _assert_cert_status(self, *expected_statuses):
        """Check the example certificate status. """
        actual_status = certs_api.example_certificates_status(self.COURSE_KEY)
        self.assertEqual(list(expected_statuses), actual_status)


@override_settings(FEATURES=FEATURES_WITH_CERTS_ENABLED)
@attr(shard=1)
class CertificatesBrandingTest(TestCase):
    """Test certificates branding. """

    COURSE_KEY = CourseLocator(org='test', course='test', run='test')
    configuration = {
        'logo_image_url': 'test_site/images/header-logo.png',
        'SITE_NAME': 'test_site.localhost',
        'urls': {
            'ABOUT': 'test-site/about',
            'PRIVACY': 'test-site/privacy',
            'TOS_AND_HONOR': 'test-site/tos-and-honor',
        },
    }

    @with_site_configuration(configuration=configuration)
    def test_certificate_header_data(self):
        """
        Test that get_certificate_header_context from lms.djangoapps.certificates api
        returns data customized according to site branding.
        """
        # Generate certificates for the course
        CourseModeFactory.create(course_id=self.COURSE_KEY, mode_slug=CourseMode.HONOR)
        data = certs_api.get_certificate_header_context(is_secure=True)

        # Make sure there are not unexpected keys in dict returned by 'get_certificate_header_context'
        self.assertItemsEqual(
            data.keys(),
            ['logo_src', 'logo_url']
        )
        self.assertIn(
            self.configuration['logo_image_url'],
            data['logo_src']
        )

        self.assertIn(
            self.configuration['SITE_NAME'],
            data['logo_url']
        )

    @with_site_configuration(configuration=configuration)
    def test_certificate_footer_data(self):
        """
        Test that get_certificate_footer_context from lms.djangoapps.certificates api returns
        data customized according to site branding.
        """
        # Generate certificates for the course
        CourseModeFactory.create(course_id=self.COURSE_KEY, mode_slug=CourseMode.HONOR)
        data = certs_api.get_certificate_footer_context()

        # Make sure there are not unexpected keys in dict returned by 'get_certificate_footer_context'
        self.assertItemsEqual(
            data.keys(),
            ['company_about_url', 'company_privacy_url', 'company_tos_url']
        )
        self.assertIn(
            self.configuration['urls']['ABOUT'],
            data['company_about_url']
        )
        self.assertIn(
            self.configuration['urls']['PRIVACY'],
            data['company_privacy_url']
        )
        self.assertIn(
            self.configuration['urls']['TOS_AND_HONOR'],
            data['company_tos_url']
        )
