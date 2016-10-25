#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from django.test.client import RequestFactory
from django.utils.duration import duration_string
from rest_framework import serializers

from courseware import grades, courses
from fields import CustomRelatedField

log = logging.getLogger(__name__)


class MetaSerializer(serializers.Serializer):
    """Serializer for the blob information in the meta attibute, will return a
    a default dict with empty values if the user does not have the information available

    """
    def to_representation(self, obj):
        # Add all the possible fields
        _fields = {
            'personal_id': None,
        }
        try:
            _data = json.loads(obj)
            _output = {}
            for key, value in _fields.iteritems():
                _output[key] = _data.get(key, value)
            return _output
        except ValueError:
            if obj:
                log.warning("Could not parse metadata during data-api call. {meta}.".format(
                    meta=obj,
                ))
            return _fields


class UserSerializer(serializers.Serializer):
    """
    Serializer for the nested set of variables a user may include
    """
    # ####################################
    # From django.contrib.auth.models.User
    # ####################################

    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=200, read_only=True)
    first_name = serializers.CharField(max_length=200, read_only=True)
    last_name = serializers.CharField(max_length=200, read_only=True)
    email = serializers.CharField(max_length=200, read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    # #################################################
    # From common.djangoapps.student.models.UserProfile
    # #################################################

    name = serializers.CharField(max_length=255, source="profile.name", read_only=True)
    meta = MetaSerializer(source="profile.meta", read_only=True)
    language = serializers.CharField(max_length=255, source="profile.language", read_only=True)
    location = serializers.CharField(max_length=255, source="profile.location", read_only=True)
    year_of_birth = serializers.IntegerField(source="profile.year_of_birth", read_only=True)

    gender = serializers.CharField(source="profile.gender", read_only=True)
    gender_display = serializers.CharField(source="profile.gender_display", read_only=True)

    level_of_education = serializers.CharField(source="profile.level_of_education", read_only=True)
    level_of_education_display = serializers.CharField(source="profile.level_of_education_display", read_only=True)

    mailing_address = serializers.CharField(source="profile.mailing_address", read_only=True)
    city = serializers.CharField(source="profile.city", read_only=True)
    country = serializers.CharField(source="profile.country", read_only=True)
    goals = serializers.CharField(source="profile.goals", read_only=True)
    bio = serializers.CharField(source="profile.bio", max_length=3000, read_only=True)

    # TODO: should we add this?
    # has_profile_image
    # courseware = models.CharField(blank=True, max_length=255, default='course.xml')  # TODO: what is this?
    # allow_certificate = models.BooleanField(default=1)  # TODO: what is this?

    # ######################################################
    # From common.djangoapps.student.models.UserSignupSource
    # ######################################################

    site = CustomRelatedField(source='usersignupsource_set', field='site', many=True)


class CourseEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for the Course enrollment model
    """
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    course_id = serializers.CharField(max_length=255, read_only=True)
    created = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    mode = serializers.CharField(max_length=100, read_only=True)


class CourseEnrollmentWithGradesSerializer(CourseEnrollmentSerializer):
    """
    Serializer for the course enrollment model, extracting grades
    """
    grades = serializers.SerializerMethodField()

    def get_grades(self, obj):
        course = courses.get_course_by_id(obj.course_id)
        user = obj.user
        gradeset = grades.grade(user, course, False)
        return gradeset


class CertificateSerializer(serializers.Serializer):
    """
    Serializer for Generated Certificates
    """
    # ####################################
    # From certificates.models.GeneratedCertificate
    # ####################################

    username = serializers.CharField(max_length=150,source='user.username', read_only=True)
    name = serializers.CharField(max_length=255, source='user.profile.name' ,read_only=True)
    course_id = serializers.CharField(max_length=255, read_only=True)
    grade = serializers.FloatField(read_only=True)
    status = serializers.CharField(max_length=100, read_only=True)
    email = serializers.CharField(max_length=200, source='user.email' ,read_only=True)
    download_url = serializers.CharField(max_length=128, read_only=True)
    verify_uuid = serializers.CharField(max_length=32, read_only=True)
    name_printed_on_certificate = serializers.CharField(max_length=255, source='name', read_only=True)
    mode = serializers.CharField(max_length=32, read_only=True)
    created_date = serializers.DateTimeField(read_only=True)
    modified_date = serializers.DateTimeField(read_only=True)
    key = serializers.CharField(max_length=32, read_only=True)

class ProctoredExamStudentAttemptSerializer(serializers.Serializer):
    """
    Serializer for proctored exams attempts made by students
    """
    # ####################################
    # From edx_proctoring.models.ProctoredExamStudentAttempt
    # ####################################

    username = serializers.CharField(max_length=150,source='user.username', read_only=True)
    name = serializers.CharField(max_length=255, source='user.profile.name' ,read_only=True)
    email = serializers.CharField(max_length=200, source='user.email' ,read_only=True)
    status = serializers.CharField(max_length=64, read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    exam_name = serializers.CharField(
        source='proctored_exam.exam_name',
        read_only=True)
    course_id = serializers.CharField(
        max_length=255,
        source='proctored_exam.course_id',
        read_only=True)

    time_taken = serializers.SerializerMethodField()
    def get_time_taken(self, obj):

        try:
            time_diff = obj.completed_at - obj.started_at
            result = duration_string(time_diff)
        except TypeError:
            result = None

        return result
