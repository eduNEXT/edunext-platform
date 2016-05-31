#!/usr/bin/python
# -*- coding: utf-8 -*-
from rest_framework import routers
from viewsets import (
    UsersViewSet,
    CourseEnrollmentViewset,
    CourseEnrollmentWithGradesViewset,
)


router = routers.DefaultRouter()
router.register(r'users', UsersViewSet)
router.register(r'course-enrollments', CourseEnrollmentViewset)
# Async operations
router.register(r'async/course-enrollments-grades', CourseEnrollmentWithGradesViewset)
