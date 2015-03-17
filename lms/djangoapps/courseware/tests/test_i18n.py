"""
Tests i18n in courseware
"""
import re

from django.test import TestCase
from django.test.utils import override_settings

from xmodule.modulestore.tests.django_utils import TEST_DATA_MOCK_MODULESTORE


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE, LANGUAGES=(('eo', 'Esperanto'),))
class I18nTestCase(TestCase):
    """
    Tests for i18n
    """
    def test_default_is_en(self):
        response = self.client.get('/')
        self.assertIn('<html lang="en">', response.content)
        self.assertEqual(response['Content-Language'], 'en')
        self.assertTrue(re.search('<body.*class=".*lang_en">', response.content))

    #EDUNEXT:LC the language wont depend on the http accept language, but the language set by the user
    # which normaly is changed via '/changelang/'
    # Language should not change wit accept language 
    def test_accept_language_wont_change_language(self):
         response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='eo')
         self.assertIn('<html lang="en">', response.content)
         self.assertEqual(response['Content-Language'], 'en')
         self.assertTrue(re.search('<body.*class=".*lang_en">', response.content))
         
    #EDUNEXT:LC /changelang/ should work and language should change acordingly
    def test_esperanto(self):
        response = self.client.post('/changelang/', {"language":"eo"})
        self.failUnlessEqual(response.status_code, 302) 
        response = self.client.get('/')
        self.assertIn('<html lang="eo">', response.content)
        self.assertEqual(response['Content-Language'], 'eo')
        self.assertTrue(re.search('<body.*class=".*lang_eo">', response.content))

    
    
