"""
This module defines the signals supported for public consumption.

This definition is still experimental. See: https://docs.google.com/document/d/1jhnudz6AVtVt0ZSRSwOwj9gJ0lsDDn_8mUCPehLPzLw/edit
"""
import django.dispatch


# This definition is the first POC used in production for adding additional business rules to the enrollment
pre_enrollment = django.dispatch.Signal(providing_args=[
    "user",
    "course_key",
    "mode",
])
