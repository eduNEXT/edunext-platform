"""
Microsite aware user preferences
"""

from lang_pref.api import released_languages
from openedx.conf import settings


def ma_lang_user_preference(user_pref):
    """
        Get a language user preference that is contained in the released LANGUAGES
        or return the default language as the user preference
    """
    released_languages_list = released_languages()
    if user_pref not in released_languages_list:
        user_pref = settings.LANGUAGE_CODE
    return user_pref
