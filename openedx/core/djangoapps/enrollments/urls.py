"""
URLs for the Enrollment API

"""


from django.conf import settings
from django.conf.urls import url

from .views import (
    CourseEnrollmentsApiListView,
    EnrollmentCourseDetailView,
    EnrollmentListView,
    EnrollmentUserRolesView,
    EnrollmentView,
    UnenrollmentView,
    SubmissionHistoryView,
)

urlpatterns = [
    url(r'^enrollment/{username},{course_key}$'.format(
        username=settings.USERNAME_PATTERN,
        course_key=settings.COURSE_ID_PATTERN),
        EnrollmentView.as_view(), name='courseenrollment'),
    url(fr'^enrollment/{settings.COURSE_ID_PATTERN}$',
        EnrollmentView.as_view(), name='courseenrollment'),
    url(r'^enrollment$', EnrollmentListView.as_view(), name='courseenrollments'),
    url(r'^enrollments/?$', CourseEnrollmentsApiListView.as_view(), name='courseenrollmentsapilist'),
    url(fr'^course/{settings.COURSE_ID_PATTERN}$',
        EnrollmentCourseDetailView.as_view(), name='courseenrollmentdetails'),
    url(r'^unenroll/$', UnenrollmentView.as_view(), name='unenrollment'),
    url(r'^roles/$', EnrollmentUserRolesView.as_view(), name='roles'),
    url(r'^submission_history$', SubmissionHistoryView.as_view(), name='submissionhistory'),
]
