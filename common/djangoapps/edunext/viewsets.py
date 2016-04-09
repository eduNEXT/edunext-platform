#!/usr/bin/python
# -*- coding: utf-8 -*-
from rest_framework import viewsets, mixins, filters
from django.contrib.auth.models import User

from student.models import CourseEnrollment
from microsite_api.authenticators import MicrositeManagerAuthentication

from filters import UserFilter, CourseEnrollmentFilter
from serializers import UserSerializer, CourseEnrollmentSerializer
from paginators import DataApiResultsSetPagination


class DataApiViewSet(mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    """
    A generic viewset for all the instances of the data-api
    """
    authentication_classes = (MicrositeManagerAuthentication,)

    pagination_class = DataApiResultsSetPagination
    filter_backends = (filters.DjangoFilterBackend,)
    prefetch_fields = False

    def get_queryset(self):
        if not self.prefetch_fields:
            return self.queryset
        return self.add_prefetch_fields_to_queryset(self.queryset, self.prefetch_fields)

    def add_prefetch_fields_to_queryset(self, queryset, fields=[]):

        for val in fields:
            if val.get("type", "") == "prefetch":
                queryset = queryset.prefetch_related(val.get("name", ""))
            else:
                queryset = queryset.select_related(val.get("name", ""))

        return queryset


class UsersViewSet(DataApiViewSet):
    """
    A viewset for viewing users in the platform.
    """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filter_class = UserFilter
    prefetch_fields = [
        {
            "name": "profile",
            "type": "select"
        },
        {
            "name": "usersignupsource_set",
            "type": "prefetch"
        }
    ]


class CourseEnrrollmentsviewsets(DataApiViewSet):
    """
    A viewset for viewing Course Enrollments.
    """
    serializer_class = CourseEnrollmentSerializer
    queryset = CourseEnrollment.objects.all()
    filter_class = CourseEnrollmentFilter
