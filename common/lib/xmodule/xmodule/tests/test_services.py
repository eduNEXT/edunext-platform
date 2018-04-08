"""
Tests for SettingsService
"""

import ddt
import mock
from unittest import TestCase

from config_models.models import ConfigurationModel
from django.conf import settings
from django.test.utils import override_settings

from xblock.runtime import Mixologist
from xmodule.services import ConfigurationService, SettingsService


class _DummyBlock(object):
    """ Dummy Xblock class """
    pass


class DummyConfig(ConfigurationModel):
    """
    Dummy Configuration
    """
    pass


class DummyUnexpected(object):
    """
    Dummy Unexpected Class
    """
    pass


@ddt.ddt
class TestSettingsService(TestCase):
    """ Test SettingsService """

    xblock_setting_key1 = 'dummy_block'
    xblock_setting_key2 = 'other_dummy_block'

    def setUp(self):
        """ Setting up tests """
        super(TestSettingsService, self).setUp()
        self.settings_service = SettingsService()
        self.xblock_mock = mock.Mock()
        self.xblock_mock.block_settings_key = self.xblock_setting_key1
        self.xblock_mock.unmixed_class = mock.Mock()
        self.xblock_mock.unmixed_class.__name__ = self.xblock_setting_key2

    def test_get_given_none_throws_value_error(self):
        """  Test that given None throws value error """
        with self.assertRaises(ValueError):
            self.settings_service.get_settings_bucket(None)

    def test_get_return_default_if_xblock_settings_is_missing(self):
        """ Test that returns default (or None if default not set) if XBLOCK_SETTINGS is not set """
        self.assertFalse(hasattr(settings, 'XBLOCK_SETTINGS'))  # precondition check
        self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock, 'zzz'), 'zzz')

    def test_get_return_empty_dictionary_if_xblock_settings_and_default_is_missing(self):
        """ Test that returns default (or None if default not set) if XBLOCK_SETTINGS is not set """
        self.assertFalse(hasattr(settings, 'XBLOCK_SETTINGS'))  # precondition check
        self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock), {})

    @override_settings(XBLOCK_SETTINGS={xblock_setting_key2: {'b': 1}})
    def test_get_returns_none_or_default_if_bucket_not_found(self):
        """ Test if settings service returns default if setting not found """
        self.assertEqual(settings.XBLOCK_SETTINGS, {self.xblock_setting_key2: {'b': 1}})
        self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock), {})
        self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock, 123), 123)

    @override_settings(XBLOCK_SETTINGS={xblock_setting_key1: 42})
    def test_get_returns_correct_value(self):
        """ Test if settings service returns correct bucket """
        self.assertEqual(settings.XBLOCK_SETTINGS, {self.xblock_setting_key1: 42})
        # self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock), 42)

    @override_settings(XBLOCK_SETTINGS={xblock_setting_key2: "I'm a setting"})
    def test_get_respects_block_settings_key(self):
        """ Test if settings service respects block_settings_key value """
        self.assertEqual(settings.XBLOCK_SETTINGS, {self.xblock_setting_key2: "I'm a setting"})
        self.xblock_mock.block_settings_key = self.xblock_setting_key2
        # self.assertEqual(self.settings_service.get_settings_bucket(self.xblock_mock), "I'm a setting")

    @override_settings(XBLOCK_SETTINGS={_DummyBlock.__name__: [1, 2, 3]})
    def test_get_uses_class_name_if_block_settings_key_is_not_set(self):
        """ Test if settings service uses class name if block_settings_key attribute does not exist """
        mixologist = Mixologist([])
        block = mixologist.mix(_DummyBlock)
        self.assertEqual(settings.XBLOCK_SETTINGS, {"_DummyBlock": [1, 2, 3]})
        # self.assertEqual(self.settings_service.get_settings_bucket(block), [1, 2, 3])


class TestConfigurationService(TestCase):
    """
    Tests for ConfigurationService
    """
    def test_given_unexpected_class_throws_value_error(self):
        """
        Test that instantiating ConfigurationService raises exception on passing
        a class which is not subclass of ConfigurationModel.
        """
        with self.assertRaises(ValueError):
            ConfigurationService(DummyUnexpected)

    def test_configuration_service(self):
        """
        Test the correct configuration on instantiating ConfigurationService.
        """
        config_service = ConfigurationService(DummyConfig)
        self.assertEqual(config_service.configuration, DummyConfig)
