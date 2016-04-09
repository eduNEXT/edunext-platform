#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from rest_framework import serializers
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
    user_id = serializers.IntegerField(read_only=True)
    course_id = serializers.CharField(max_length=255, read_only=True)
    created = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    mode = serializers.CharField(max_length=100, read_only=True)
