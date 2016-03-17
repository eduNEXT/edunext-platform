#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Parses an xml created by mysqldump --xml
import sys
from pprint import pformat as pf
from xml_dump_parser import XmlDumpParser, TableJoiner
from creators.user_creator import UserCreator
from creators.user_enrollment_creator import UserEnrollmentCreator
from creators.studentmodule_creator import StudentmoduleCreator
import logging

logger = logging.getLogger(__name__)


class DatabaseXmlDumpImporter:
    """
    Class for importing as a microsite a database that was dumped with --xml
    """
    xmlDumpParser = None
    imported_users = []
    dry_run = False

    def __init__(self, filename, dry_run=False):
        """Initialize importer with the filename.
        Args:
            filename (str): File name with location to import. e.g. '/var/tmp/database.xml'
        """
        logger.debug("Procesing: {}".format(filename))
        self.xmlDumpParser = XmlDumpParser(filename)
        self.dry_run = dry_run

    def import_users(self, user_ids=[], microsite_hostname=None):
        """
        Import the users, creating them and activating them. Return list of users created.
        """
        user_joiner = TableJoiner('auth_user', 'auth_userprofile', 'id', 'user_id')
        row_list = self.xmlDumpParser.process_join(user_joiner)
        # Get rows to import
        users = [row for row in row_list if int(row['auth_user-id']) in user_ids]

        userCreators = []
        has_conflicts = False
        # Test creation
        for user_dic in users:
            userCreator = UserCreator(user_dic, microsite_hostname)
            has_conflicts = not userCreator.check_user_creation() or has_conflicts
            userCreators.append(userCreator)
        if has_conflicts:
            exit()
            # raise Exception("Can't create the users given, check warning messages.")
        # Create users
        if self.dry_run:
            logger.debug("Dry run. Would import following users:")
            logger.debug(userCreators)
            return []
        for userCreator in userCreators:
            (user, profile) = userCreator.create_user()
            new_user_dic = {'old_user_id': userCreator.get_old_user_id(),
                            'new_user_id': user.id,
                            'old_profile_id': userCreator.get_old_profile_id(),
                            'new_profile_id': profile.id,
                            'username': user.username,
                            'email': user.email
                            }
            self.imported_users.append(new_user_dic)
        return self.imported_users

    def enroll_users(self, imported_users_list):
        enrollments_list = self.xmlDumpParser.process_table('student_courseenrollment')
        imported_enrollments = []
        for user in imported_users_list:
            user_enrollments = [row for row in enrollments_list if user['old_user_id'] == int(row['user_id'])]
            for user_enrollment in user_enrollments:
                # logger.debug("\nuser_enrollment:\n"+pf(user_enrollment, indent=4))
                enrollment_creator = UserEnrollmentCreator(user, user_enrollment)
                enrollment = enrollment_creator.enroll_user()
                new_enrollment_dic = {'old_user_id': user['old_user_id'],
                                      'new_user_id': user['new_user_id'],
                                      'old_enrollment_id': user_enrollment['id'],
                                      'new_enrollment_id': enrollment.id,
                                      'course_id': user_enrollment['course_id']
                                      }
                imported_enrollments.append(new_enrollment_dic)
        return imported_enrollments

    def import_studentmodule(self, user_list):
        """
        """
        # get all courseware_studentmodule for old_ids
        states = self.xmlDumpParser.process_table('courseware_studentmodule')

        store = {}
        for state in states:
            user_id = long(state.get("student_id"))

            try:
                store[user_id].append(state)
            except KeyError:
                store[user_id] = []
                store[user_id].append(state)

        student_modules_imported = []
        for user in user_list:
            old_user_id = user.get('old_user_id')
            new_user_id = user.get('new_user_id')

            old_states = store.get(old_user_id, [])

            # create all courseware_studentmodule for new_ids
            creator = StudentmoduleCreator(new_user_id, old_states)
            user_student_modules = creator.insert_all_states()
            for student_module in user_student_modules:
                student_module_dic = {"new_id": student_module.id,
                                      "old_id": student_module.old_id,
                                      "module_id": str(student_module.module_state_key),
                                      "course_id": str(student_module.course_id),
                                      'old_user_id': old_user_id,
                                      'new_user_id': new_user_id,
                                     }
                student_modules_imported.append(student_module_dic)
        return student_modules_imported


def main():
    # tables_to_process = ['auth_user', 'auth_userprofile']
    if len(sys.argv) < 2:
        logger.error("Please give a filename of the xml dump to process")
        return 1
    filename = sys.argv[1]
    importer = DatabaseXmlDumpImporter(filename)
    importer.importUsers()


if __name__ == "__main__":
    main()
