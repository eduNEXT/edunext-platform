# -*- coding: utf-8 -*-

""" Overrides for production eduNEXT installations. """

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=wildcard-import, unused-wildcard-import

from .aws import *


# Reading setting to skip or not the enrollment start date filtering for edx-search
SEARCH_SKIP_ENROLLMENT_START_DATE_FILTERING = ENV_TOKENS.get(
    'SEARCH_SKIP_ENROLLMENT_START_DATE_FILTERING',
    SEARCH_SKIP_ENROLLMENT_START_DATE_FILTERING
)
