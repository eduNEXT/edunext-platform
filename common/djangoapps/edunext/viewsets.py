#!/usr/bin/python
# -*- coding: utf-8 -*-
import random
from datetime import datetime

from rest_framework import viewsets, mixins, filters, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from student.models import CourseEnrollment
from certificates.models import GeneratedCertificate
from microsite_api.authenticators import MicrositeManagerAuthentication

from filters import (
    UserFilter,
    CourseEnrollmentFilter,
    GeneratedCerticatesFilter)
from serializers import (
    UserSerializer,
    CourseEnrollmentSerializer,
    CertificateSerializer
)
from paginators import DataApiResultsSetPagination
from tasks import EnrollmentsGrades


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


class CourseEnrollmentViewset(DataApiViewSet):
    """
    A viewset for viewing Course Enrollments.
    """
    serializer_class = CourseEnrollmentSerializer
    queryset = CourseEnrollment.objects.all()
    filter_class = CourseEnrollmentFilter


class CourseEnrollmentWithGradesViewset(DataApiViewSet):
    """
    A viewset for viewing Course Enrollments with grades data.
    This view will create a celery task to fetch grades data for
    enrollments in the background, and will return the id of the
    celery task
    """
    serializer_class = CourseEnrollmentSerializer
    queryset = CourseEnrollment.objects.all()
    filter_class = CourseEnrollmentFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        now_date = datetime.now()
        string_now_date = now_date.strftime("%Y-%m-%d-%H-%M-%S")
        randnum = random.randint(100, 999)
        task_id = "data_api-" + string_now_date + "-" + str(randnum)

        named_args = {
            "data": serializer.data,
        }
        task_instance = EnrollmentsGrades()
        res = task_instance.apply_async(
            kwargs=named_args,
            task_id=task_id,
            routing_key=settings.GRADES_DOWNLOAD_ROUTING_KEY
        )

        url_task_status = request.build_absolute_uri(
            reverse("celery-data-api-tasks", kwargs={"task_id": task_id})
        )
        data_response = {
            "task_id": res.id,
            "task_url": url_task_status,
        }
        return Response(data_response, status=status.HTTP_202_ACCEPTED)


class CertificateViewSet(DataApiViewSet):
    """
    A viewset for viewing certificates in the platform.
    """
    serializer_class = CertificateSerializer
    queryset = GeneratedCertificate.objects.all()
    filter_class = GeneratedCerticatesFilter
    prefetch_fields = [
        {
            "name": "user",
            "type": "select"
        }

    ]
