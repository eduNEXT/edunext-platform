#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import six
from rest_framework import relations


class CustomRelatedField(relations.RelatedField):
    """
    A read only field that represents its targets using the site field
    """

    def __init__(self, **kwargs):
        kwargs['read_only'] = True
        self.field = kwargs.pop('field')
        super(CustomRelatedField, self).__init__(**kwargs)

    def to_representation(self, instance):
        return six.text_type(getattr(instance, self.field))
