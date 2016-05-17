#!/usr/bin/python
# -*- coding: utf-8 -*-
import django_filters

from rest_framework import filters
from django.contrib.auth.models import User

from student.models import CourseEnrollment
from opaque_keys.edx.keys import CourseKey


class BaseDataApiFilter(filters.FilterSet):
    order_by_field = "ordering"


class UserFilter(BaseDataApiFilter):
    # Filtering by main model fields
    username = django_filters.CharFilter(lookup_type='icontains')
    first_name = django_filters.CharFilter(lookup_type='icontains')
    last_name = django_filters.CharFilter(lookup_type='icontains')
    email = django_filters.CharFilter(lookup_type='iexact')
    is_active = django_filters.BooleanFilter()
    date_joined = django_filters.DateTimeFromToRangeFilter()

    # Filtering by user profile fields
    name = django_filters.CharFilter(name="profile__name", lookup_type="icontains")
    language = django_filters.CharFilter(name="profile__language", lookup_type="iexact")
    year_of_birth = django_filters.RangeFilter(name="profile__year_of_birth")
    gender = django_filters.CharFilter(name="profile__gender", lookup_type="iexact")
    mailing_address = django_filters.CharFilter(name="profile__mailing_address", lookup_type="iexact")
    city = django_filters.CharFilter(name="profile__city", lookup_type="icontains")
    country = django_filters.CharFilter(name="profile__country", lookup_type="iexact")

    # Filtering by user signup source fields
    site = django_filters.CharFilter(name="usersignupsource__site", lookup_type='iexact')

    class Meta:
        model = User
        fields = [
                 'id',
                 'username',
                 'first_name',
                 'last_name',
                 'email',
                 'is_active',
                 'date_joined',
                 'name',
                 'language',
                 'year_of_birth',
                 'gender',
                 'mailing_address',
                 'city',
                 'country',
                 'site',
                ]
        order_by = True


class CourseEnrollmentFilter(BaseDataApiFilter):

    course_id = django_filters.MethodFilter()
    created = django_filters.DateTimeFromToRangeFilter()
    is_active_enrollment = django_filters.BooleanFilter(name="is_active")
    mode = django_filters.CharFilter(lookup_type='iexact')
    site = django_filters.CharFilter(name="user__usersignupsource__site", lookup_type='iexact')

    def filter_course_id(self, queryset, value):
        """
        This custom filter was created to enable filtering by course_id.

        See common.djangoapps.xmodule_django.models

        When doing queries over opaque fields, we need to instance the
        KEY_CLASS of the field with the query string first, and then pass
        this instance to the queryset filter.
        In this case, the KEY_CLASS for course_id field is CourseKey
        """
        if value:
            # CourseKey instance creation will fail if course does not exist
            try:
                # Instantiating CourseKey of the field with query string
                instance = CourseKey.from_string(str(value))
                # Passing instance to queryset filter
                return queryset.filter(course_id=instance)
            except:
                # If CourseKey instantiation fails, return an empty queryset
                return queryset.none()

        return queryset

    class Meta:
        model = CourseEnrollment
        fields = [
                 'id',
                 'course_id',
                 'created',
                 'is_active_enrollment',
                 'mode',
                 'site',
        ]
        order_by = True
