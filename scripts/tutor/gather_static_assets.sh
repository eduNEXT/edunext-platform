#!/bin/bash -e

set -x

THEME_DIRS=${THEME_DIRS:-/openedx/themes/ednx-saas-themes/edx-platform}
THEMES=${THEMES:-bragi}

chmod a+x /openedx/bin/*
export PATH=/openedx/bin:${PATH}
export NO_PYTHON_UNINSTALL=1
export NO_PREREQ_INSTALL=1

openedx-assets xmodule \
    && openedx-assets npm \
    && openedx-assets webpack --env=prod \
    && openedx-assets common

openedx-assets themes --theme-dirs $THEME_DIRS --themes $THEMES  \
    && openedx-assets collect --settings=tutor.assets
