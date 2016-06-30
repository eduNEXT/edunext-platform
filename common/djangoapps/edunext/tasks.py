#!/usr/bin/python
# -*- coding: utf-8 -*-
from celery import Task

from student.models import CourseEnrollment

from serializers import CourseEnrollmentWithGradesSerializer


class EnrollmentsGrades(Task):

    def run(self, data):
        """
        This task receives a list with enrollments, and returns the same
        enrollments with grades data
        """
        try:
            enrollments_ids = [el["id"] for el in data]
            enrollments_queryset = CourseEnrollment.objects.filter(id__in=enrollments_ids)

            serializer = CourseEnrollmentWithGradesSerializer(enrollments_queryset, many=True)

            return serializer.data
        except Exception as e:
            # Here we can log an error when something went wrong
            return []
