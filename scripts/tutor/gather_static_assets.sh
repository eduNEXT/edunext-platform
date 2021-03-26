#!/bin/bash -e

set -x

THEME_DIRS=${THEME_DIRS:-/openedx/themes/ednx-saas-themes/edx-platform}
THEMES=${THEMES:-bragi}

export NO_PYTHON_UNINSTALL=1
export NO_PREREQ_INSTALL=1

cd /openedx/edx-platform

# openedx-assets xmodule \
#     && openedx-assets npm \
#     && openedx-assets webpack --env=prod \
#     && openedx-assets common

openedx-assets themes --theme-dirs $THEME_DIRS --themes $THEMES  \
    && openedx-assets collect --settings=tutor.assets
