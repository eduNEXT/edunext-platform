#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.db import transaction
from django.contrib.auth.models import User
from student.views import _do_create_account, AccountValidationError
from student.models import CourseEnrollment, create_comments_service_user
from student.forms import AccountCreationForm
from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from student.models import UserSignupSource
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from opaque_keys import InvalidKeyError
from courseware.models import StudentModule
from pprint import pformat as pf
import logging

logger = logging.getLogger(__name__)


def create_complete_account(data, profile_data, site=None):
    """Create/Import a user account. Activate the user.
    Args:
        data (dict): User main data.
        profile_data (dict): profile data.
    Raises:
        Exception: If the account already exists (email or username repeated).
    Returns:
       Tuple : user and profile objects.
    """
    conflicts = check_create_complete_account(data, profile_data)
    if conflicts:
        # Maybe ask what to do? how to change username?
        raise Exception("{} conflicts for {} , {}.".format(conflicts, data['email'], data['username']))

    # Go ahead and create the new user
    form = AccountCreationForm(
        data=data,
        extra_fields=profile_data,
        tos_required=False,
    )
    try:
        (user, profile, registration) = _do_create_account(form)
        registration.activate()
        registration.save()
    except AccountValidationError as e:
        logger.error(e.message)

    # create_comments_service_user(user)
    if site:
        user_signup_source = UserSignupSource(user=user, site=site)
        user_signup_source.save()
    return (user, profile)


def check_create_complete_account(data, profile_data):
    conflicts = check_account_exists(email=data['email'], username=data['username'])
    return conflicts


def enroll_student(course_id, user_id, enrollment_mode):
    try:
        course = CourseKey.from_string(course_id)
        # if it's not a new-style course key, parse it from an old-style
        # course key
    except InvalidKeyError:
        course = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    # Enroll the user in a course
    user = User.objects.get(pk=user_id)
    if course is not None:
        if CourseEnrollment.objects.filter(course_id=course).count() == 0:
            logger.warning("The course {} had no other register in the table, (it is posible the course doesn't exist)".format(course_id))
        enrollment = CourseEnrollment.enroll(user, course, mode=enrollment_mode)
        return enrollment
    else:
        print "Warning: Course key was not given"


def create_courseware_studentmodule(data):
    """This function will create a record in the courseware_studentmodule table
    Args:
        data (dict): represents the object, with all the required fields as it should be stored
    """
    logger.debug("StudentModule data to import"+pf(data))
    with transaction.atomic():
        student_module = StudentModule.objects.create(student_id=data['student_id'], module_state_key=data['module_id'])
        student_module.module_type = data['module_type']
        student_module.course_id = data['course_id']
        student_module.state = data['state']
        student_module.grade = data['grade']
        student_module.max_grade = data['max_grade']
        student_module.done = data['done']
        student_module.created = data['created']
        student_module.modified = data['modified']
        student_module.save()
    student_module.old_id = data['id']
    return student_module
