"""
Microsite aware language filter
"""

from lang_pref.api import released_languages
from openedx.conf import settings


def ma_language(language):
    """
        Returns a microsite aware language for the language received, using the released_languages setting.
        If the language is not released return the default: LANGUAGE_CODE
        If is None, leave it alone.
    """
    released_languages_list = released_languages()
    released_languages_code_list = {langObj.code for langObj in released_languages_list}

    if language and language not in released_languages_code_list:
        language = settings.LANGUAGE_CODE
    return language
