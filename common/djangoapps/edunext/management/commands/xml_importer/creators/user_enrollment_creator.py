#!/usr/bin/env python
# -*- coding: utf-8 -*-
import edxapp_interface


class UserEnrollmentCreator:
    """Enrollment importer, from an imported user imports its course enrollments.
    Attributes:
        course_id (str): Course id e.g. 'course-v1:test+test1+2016-1'
        enrollment_dic (dic): Enrollment
        enrollment_mode (str): 'audit' 'honor' ...
        new_user_id (int): new user id
        user_dic (dic): imported user dic
    """
    def __init__(self, user_dic, enrollment_dic):
        """Initialize user enrollment creator
        Args:
            user_dic (dic): imported user dic
            enrollment_dic (dic): student_courseenrollment row with columnames as keys
        """
        self.user_dic = user_dic
        self.enrollment_dic = enrollment_dic

        self.course_id = enrollment_dic['course_id']
        self.new_user_id = user_dic['new_user_id']
        self.enrollment_mode = enrollment_dic['mode']

    def enroll_user(self):
        """Enroll the user, return enrollment object
        Returns:
            CourseEnrollment: Enrollment object
        """
        enrollment = edxapp_interface.enroll_student(self.course_id, self.new_user_id, self.enrollment_mode)
        return enrollment
