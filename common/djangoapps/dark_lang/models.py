"""
Models for the dark-launching languages
"""
from django.db import models

from config_models.models import ConfigurationModel
from microsite_configuration import microsite


class DarkLangConfig(ConfigurationModel):
    """
    Configuration for the dark_lang django app
    """
    released_languages = models.TextField(
        blank=True,
        help_text="A comma-separated list of language codes to release to the public."
    )

    @property
    def released_languages_list(self):
        """
        ``released_languages`` as a list of language codes.

        Example: ['it', 'de-at', 'es', 'pt-br']
        """
        released_languages = microsite.get_value('released_languages', self.released_languages)

        if not released_languages.strip():  # pylint: disable=no-member
            return []

        languages = [lang.lower().strip() for lang in released_languages.split(',')]  # pylint: disable=no-member
        # Put in alphabetical order
        languages.sort()
        return languages
