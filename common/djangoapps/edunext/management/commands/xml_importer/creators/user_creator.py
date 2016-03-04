#!/usr/bin/env python
# -*- coding: utf-8 -*-
import edxapp_interface
import logging

logger = logging.getLogger(__name__)


class UserCreator:
    """User importer, imports a user to the current edxapp installation.
    Attributes:
        meta (str): User metadata
        password (str): User hashed password
        profile_data (dict): Profile data
        profile_fields (list of str): Fields of the profile to fill with equaly named columns from user_dict
        user_data (dict): Main User data
    """
    profile_fields = [
        "name", "level_of_education", "gender", "mailing_address", "city", "country", "goals",
        "year_of_birth"
    ]

    def __init__(self, user_dict, site):
        """Initialize user creator with a dictionary of the user to create.
        Args:
            user_dict (dict): column names as keys with the table where they come appended.
        """
        self.user_data = {
                     "username": user_dict['auth_user-username'],
                     "email": user_dict['auth_user-email'],
                     "password": "default_password",
                     "name": user_dict['auth_userprofile-name']
                    }
        self.profile_data = {}
        for field in self.profile_fields:
            self.profile_data[field] = user_dict['auth_userprofile-{}'.format(field)]

        self.password = user_dict['auth_user-password']
        self.meta = user_dict['auth_userprofile-meta']
        self.old_id = int(user_dict['auth_user-id'])
        self.old_profile_id = int(user_dict['auth_userprofile-id'])
        self.site = site

    def create_user(self):
        """Create the user with apropiate values.
        Returns:
            tuple: user and profile objects.
        """
        (user, profile) = edxapp_interface.create_complete_account(self.user_data, self.profile_data, self.site)
        user.password = self.password
        user.save()
        profile.meta = self.meta
        profile.save()
        # TODO set from what microsite this user is
        return (user, profile)

    def check_user_creation(self):
        """Checks if the user can be created, printing a warning if not and returning false
        Returns:
            bool: True if can be created False otherwise
        """
        conflicts = edxapp_interface.check_create_complete_account(self.user_data, self.profile_data)
        if conflicts:
            logger.warn("old_user_id:{} username:{}, email:{} has the following conflicts:{}".format(
                self.old_id, self.user_data['username'], self.user_data['email'], conflicts))
            return False
        else:
            return True

    def get_old_user_id(self):
        return self.old_id

    def get_old_profile_id(self):
        return self.old_profile_id

