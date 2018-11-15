"""
Helper functions for loading environment settings.
"""
from __future__ import print_function

import json
import os
import sys
from time import sleep

import memcache
from lazy import lazy
from path import Path as path
from paver.easy import sh

from pavelib.utils.cmd import django_cmd


def repo_root():
    """
    Get the root of the git repository (edx-platform).

    This sometimes fails on Docker Devstack, so it's been broken
    down with some additional error handling.  It usually starts
    working within 30 seconds or so; for more details, see
    https://openedx.atlassian.net/browse/PLAT-1629 and
    https://github.com/docker/for-mac/issues/1509
    """
    file_path = path(__file__)
    attempt = 1
    while True:
        try:
            absolute_path = file_path.abspath()
            break
        except OSError:
            print('Attempt {}/180 to get an absolute path failed'.format(attempt))
            if attempt < 180:
                attempt += 1
                sleep(1)
            else:
                print('Unable to determine the absolute path of the edx-platform repo, aborting')
                raise
    return absolute_path.parent.parent.parent


class Env(object):
    """
    Load information about the execution environment.
    """

    # Root of the git repository (edx-platform)
    REPO_ROOT = repo_root()

    # Reports Directory
    REPORT_DIR = REPO_ROOT / 'reports'
    METRICS_DIR = REPORT_DIR / 'metrics'
    QUALITY_DIR = REPORT_DIR / 'quality_junitxml'

    # Generic log dir
    GEN_LOG_DIR = REPO_ROOT / "test_root" / "log"

    # Python unittest dirs
    PYTHON_COVERAGERC = REPO_ROOT / ".coveragerc"

    # Bok_choy dirs
    BOK_CHOY_DIR = REPO_ROOT / "common" / "test" / "acceptance"
    BOK_CHOY_LOG_DIR = GEN_LOG_DIR
    BOK_CHOY_REPORT_DIR = REPORT_DIR / "bok_choy"
    BOK_CHOY_A11Y_REPORT_DIR = REPORT_DIR / "a11y"
    BOK_CHOY_COVERAGERC = BOK_CHOY_DIR / ".coveragerc"
    BOK_CHOY_A11Y_COVERAGERC = BOK_CHOY_DIR / ".a11ycoveragerc"
    BOK_CHOY_A11Y_CUSTOM_RULES_FILE = (
        REPO_ROOT / "node_modules" / "edx-custom-a11y-rules" /
        "lib" / "custom_a11y_rules.js"
    )

    PA11YCRAWLER_REPORT_DIR = REPORT_DIR / "pa11ycrawler"
    PA11YCRAWLER_COVERAGERC = BOK_CHOY_DIR / ".pa11ycrawlercoveragerc"

    # If set, put reports for run in "unique" directories.
    # The main purpose of this is to ensure that the reports can be 'slurped'
    # in the main jenkins flow job without overwriting the reports from other
    # build steps. For local development/testing, this shouldn't be needed.
    if os.environ.get("SHARD", None):
        shard_str = "shard_{}".format(os.environ.get("SHARD"))
        BOK_CHOY_REPORT_DIR = BOK_CHOY_REPORT_DIR / shard_str
        BOK_CHOY_LOG_DIR = BOK_CHOY_LOG_DIR / shard_str

    # For the time being, stubs are used by both the bok-choy and lettuce acceptance tests
    # For this reason, the stubs package is currently located in the Django app called "terrain"
    # where other lettuce configuration is stored.
    BOK_CHOY_STUB_DIR = REPO_ROOT / "common" / "djangoapps" / "terrain"

    # Directory that videos are served from
    VIDEO_SOURCE_DIR = REPO_ROOT / "test_root" / "data" / "video"

    # Detect if in a Docker container, and if so which one
    SERVER_HOST = os.environ.get('BOK_CHOY_HOSTNAME', '0.0.0.0')
    USING_DOCKER = SERVER_HOST != '0.0.0.0'
    SETTINGS = 'bok_choy_docker' if USING_DOCKER else 'bok_choy'
    DEVSTACK_SETTINGS = 'devstack_docker' if USING_DOCKER else 'devstack'
    TEST_SETTINGS = 'test'

    BOK_CHOY_SERVERS = {
        'lms': {
            'host': SERVER_HOST,
            'port': os.environ.get('BOK_CHOY_LMS_PORT', '8003'),
            'log': BOK_CHOY_LOG_DIR / "bok_choy_lms.log"
        },
        'cms': {
            'host': SERVER_HOST,
            'port': os.environ.get('BOK_CHOY_CMS_PORT', '8031'),
            'log': BOK_CHOY_LOG_DIR / "bok_choy_studio.log"
        }
    }

    BOK_CHOY_STUBS = {

        'xqueue': {
            'port': 8040,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_xqueue.log",
            'config': 'register_submission_url=http://0.0.0.0:8041/test/register_submission',
        },

        'ora': {
            'port': 8041,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_ora.log",
            'config': '',
        },

        'comments': {
            'port': 4567,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_comments.log",
        },

        'video': {
            'port': 8777,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_video_sources.log",
            'config': "root_dir={}".format(VIDEO_SOURCE_DIR),
        },

        'youtube': {
            'port': 9080,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_youtube.log",
        },

        'edxnotes': {
            'port': 8042,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_edxnotes.log",
        },

        'ecommerce': {
            'port': 8043,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_ecommerce.log",
        },

        'catalog': {
            'port': 8091,
            'log': BOK_CHOY_LOG_DIR / "bok_choy_catalog.log",
        },
    }

    # Mongo databases that will be dropped before/after the tests run
    MONGO_HOST = 'edx.devstack.mongo' if USING_DOCKER else 'localhost'
    BOK_CHOY_MONGO_DATABASE = "test"
    BOK_CHOY_CACHE_HOST = 'edx.devstack.memcached' if USING_DOCKER else '0.0.0.0'
    BOK_CHOY_CACHE = memcache.Client(['{}:11211'.format(BOK_CHOY_CACHE_HOST)], debug=0)

    # Test Ids Directory
    TEST_DIR = REPO_ROOT / ".testids"

    # Configured browser to use for the js test suites
    SELENIUM_BROWSER = os.environ.get('SELENIUM_BROWSER', 'firefox')
    if USING_DOCKER:
        KARMA_BROWSER = 'ChromeDocker' if SELENIUM_BROWSER == 'chrome' else 'FirefoxDocker'
    else:
        KARMA_BROWSER = 'FirefoxNoUpdates'

    # Files used to run each of the js test suites
    # TODO:  Store this as a dict. Order seems to matter for some
    # reason. See issue TE-415.
    KARMA_CONFIG_FILES = [
        REPO_ROOT / 'cms/static/karma_cms.conf.js',
        REPO_ROOT / 'cms/static/karma_cms_squire.conf.js',
        REPO_ROOT / 'cms/static/karma_cms_webpack.conf.js',
        REPO_ROOT / 'lms/static/karma_lms.conf.js',
        REPO_ROOT / 'common/lib/xmodule/xmodule/js/karma_xmodule.conf.js',
        REPO_ROOT / 'common/lib/xmodule/xmodule/js/karma_xmodule_webpack.conf.js',
        REPO_ROOT / 'common/static/karma_common.conf.js',
        REPO_ROOT / 'common/static/karma_common_requirejs.conf.js',
    ]

    JS_TEST_ID_KEYS = [
        'cms',
        'cms-squire',
        'cms-webpack',
        'lms',
        'xmodule',
        'xmodule-webpack',
        'common',
        'common-requirejs'
    ]

    JS_REPORT_DIR = REPORT_DIR / 'javascript'

    # Directories used for common/lib/tests
    IGNORED_TEST_DIRS = ('__pycache__', '.cache')
    LIB_TEST_DIRS = []
    for item in (REPO_ROOT / "common/lib").listdir():
        dir_name = (REPO_ROOT / 'common/lib' / item)
        if dir_name.isdir() and not dir_name.endswith(IGNORED_TEST_DIRS):
            LIB_TEST_DIRS.append(path("common/lib") / item.basename())
    LIB_TEST_DIRS.append(path("pavelib/paver_tests"))

    # Directory for i18n test reports
    I18N_REPORT_DIR = REPORT_DIR / 'i18n'

    # Service variant (lms, cms, etc.) configured with an environment variable
    # We use this to determine which envs.json file to load.
    SERVICE_VARIANT = os.environ.get('SERVICE_VARIANT', None)

    # If service variant not configured in env, then pass the correct
    # environment for lms / cms
    if not SERVICE_VARIANT:  # this will intentionally catch "";
        if any(i in sys.argv[1:] for i in ('cms', 'studio')):
            SERVICE_VARIANT = 'cms'
        else:
            SERVICE_VARIANT = 'lms'

    @classmethod
    def get_django_setting(cls, django_setting, system, settings=None):
        """
        Interrogate Django environment for specific settings values
        :param django_setting: the django setting to get
        :param system: the django app to use when asking for the setting (lms | cms)
        :param settings: the settings file to use when asking for the value
        :return: unicode value of the django setting
        """
        if not settings:
            settings = os.environ.get("EDX_PLATFORM_SETTINGS", "aws")
        value = sh(
            django_cmd(
                system,
                settings,
                "print_setting {django_setting} 2>/dev/null".format(
                    django_setting=django_setting
                )
            ),
            capture=True
        )
        return unicode(value).strip()

    @lazy
    def env_tokens(self):
        """
        Return a dict of environment settings.
        If we couldn't find the JSON file, issue a warning and return an empty dict.
        """

        # Find the env JSON file
        if self.SERVICE_VARIANT:
            env_path = self.REPO_ROOT.parent / "{service}.env.json".format(service=self.SERVICE_VARIANT)
        else:
            env_path = path("env.json").abspath()

        # If the file does not exist, here or one level up,
        # issue a warning and return an empty dict
        if not env_path.isfile():
            env_path = env_path.parent.parent / env_path.basename()
        if not env_path.isfile():
            print(
                "Warning: could not find environment JSON file "
                "at '{path}'".format(path=env_path),
                file=sys.stderr,
            )
            return dict()

        # Otherwise, load the file as JSON and return the resulting dict
        try:
            with open(env_path) as env_file:
                return json.load(env_file)

        except ValueError:
            print(
                "Error: Could not parse JSON "
                "in {path}".format(path=env_path),
                file=sys.stderr,
            )
            sys.exit(1)

    @lazy
    def feature_flags(self):
        """
        Return a dictionary of feature flags configured by the environment.
        """
        return self.env_tokens.get('FEATURES', dict())
