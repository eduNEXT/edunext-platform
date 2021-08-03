"""
This module defines the signals supported for public consumption.

This definition is still experimental.
See: https://docs.google.com/document/d/1jhnudz6AVtVt0ZSRSwOwj9gJ0lsDDn_8mUCPehLPzLw/edit.
"""
import django.dispatch


class TriggerException(Exception):
    """Raised when the sending of the signal of a trigger fails"""


# This definition is the first POC used in production for adding additional business rules to the enrollment
pre_enrollment = django.dispatch.Signal(providing_args=[
    "user",
    "course_key",
    "mode",
])

# Signal that fires after the user's enrollment
post_enrollment = django.dispatch.Signal(providing_args=[
    "user",
    "course_key",
    "mode",
])

# Signal that fires after a user's certificate is created
post_certificate_creation = django.dispatch.Signal(providing_args=[
    "certificate",
])

# This signal fires after a user is registered on the platform
post_register = django.dispatch.Signal(providing_args=["user"])
