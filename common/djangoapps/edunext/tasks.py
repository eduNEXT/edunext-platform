#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
TODO: add me
"""
from celery import Task

from student.models import CourseEnrollment

from edunext.serializers import CourseEnrollmentWithGradesSerializer


class EnrollmentsGrades(Task):
    """
    TODO: add me
    """

    def run(self, data, *args, **kwargs):
        """
        This task receives a list with enrollments, and returns the same
        enrollments with grades data
        """

        enrollments_ids = [el["id"] for el in data]
        enrollments_queryset = CourseEnrollment.objects.filter(id__in=enrollments_ids)

        serializer = CourseEnrollmentWithGradesSerializer(enrollments_queryset, many=True)

        return serializer.data
