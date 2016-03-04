#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import edxapp_interface

logger = logging.getLogger(__name__)


class StudentmoduleCreator(object):
    """
    """
    def __init__(self, new_user_id, old_states):
        self.states = old_states
        self.new_user_id = new_user_id

        for state in self.states:
            state['student_id'] = self.new_user_id

    def insert_all_states(self):
        """
        """
        student_modules = []
        for state in self.states:
            student_module = edxapp_interface.create_courseware_studentmodule(state)
            student_modules.append(student_module)
        return student_modules
