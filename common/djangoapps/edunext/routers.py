#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
TODO: add me
"""
from rest_framework import routers
from edunext.viewsets import (
    UsersViewSet,
    CourseEnrollmentViewset,
    CourseEnrollmentWithGradesViewset,
    CertificateViewSet,
    ProctoredExamStudentViewSet
)


ROUTER = routers.DefaultRouter()
ROUTER.register(r'users', UsersViewSet)
ROUTER.register(r'course-enrollments', CourseEnrollmentViewset)
ROUTER.register(r'certificates', CertificateViewSet)
ROUTER.register(r'proctored-exams-attempts', ProctoredExamStudentViewSet)
# Async operations
ROUTER.register(r'async/course-enrollments-grades', CourseEnrollmentWithGradesViewset)
