#!/usr/bin/python
# -*- coding: utf-8 -*-
from rest_framework.pagination import PageNumberPagination
from django.conf import settings


class DataApiResultsSetPagination(PageNumberPagination):
    """
    A subset of data of any queryset
    """
    page_size = settings.DATA_API_DEF_PAGE_SIZE
    page_size_query_param = 'page_size'
    max_page_size = settings.DATA_API_MAX_PAGE_SIZE
