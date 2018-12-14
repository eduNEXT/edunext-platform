""" Overrides for Docker-based eduNEXT devstack. """

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=wildcard-import, unused-wildcard-import

from .devstack_docker import *

############################# ADVANCED COMPONENTS #############################
FEATURES['ENABLE_CREATOR_GROUP'] = True

########################## ORGANIZATIONS APP ################################
FEATURES['ORGANIZATIONS_APP'] = True
