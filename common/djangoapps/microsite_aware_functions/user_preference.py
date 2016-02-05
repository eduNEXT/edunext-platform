"""
Microsite aware user preferences
"""

from lang_pref.api import released_languages
from openedx.conf import settings


def ma_lang_user_preference(user_pref):
    """
        Get a language user preference that is contained in the released LANGUAGES
        or return NONE with which we expect a later instance to decide the language
    """
    released_languages_list = released_languages()
    released_languages_code_list = {langObj.code for langObj in released_languages_list}

    if user_pref and user_pref not in released_languages_code_list:
        user_pref = settings.LANGUAGE_CODE
    return user_pref
