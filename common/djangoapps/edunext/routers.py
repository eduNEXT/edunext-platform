#!/usr/bin/python
# -*- coding: utf-8 -*-
from rest_framework import routers
from viewsets import (
    UsersViewSet,
    CourseEnrollmentViewset,
    CourseEnrollmentWithGradesViewset,
    CertificateViewSet,
    ProctoredExamStudentViewSet
)


router = routers.DefaultRouter()
router.register(r'users', UsersViewSet)
router.register(r'course-enrollments', CourseEnrollmentViewset)
router.register(r'certificates', CertificateViewSet)
router.register(r'proctored-exams-attempts', ProctoredExamStudentViewSet)
# Async operations
router.register(r'async/course-enrollments-grades', CourseEnrollmentWithGradesViewset)
