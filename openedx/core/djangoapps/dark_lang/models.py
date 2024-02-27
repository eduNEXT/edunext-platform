"""
Models for the dark-launching languages
"""


from config_models.models import ConfigurationModel
from django.db import models


class DarkLangConfig(ConfigurationModel):
    """
    Configuration for the dark_lang django app.

    .. no_pii:
    """
    released_languages = models.TextField(
        blank=True,
        help_text="A comma-separated list of language codes to release to the public."
    )
    enable_beta_languages = models.BooleanField(
        default=False,
        help_text="Enable partially supported languages to display in language drop down."
    )
    beta_languages = models.TextField(
        blank=True,
        help_text="A comma-separated list of language codes to release to the public as beta languages."
    )

    def __str__(self):
        return "DarkLangConfig()"

    @property
    def released_languages_list(self):
        """
        ``released_languages`` as a list of language codes.

        Example: ['it', 'de-at', 'es', 'pt-br']
        """
        if not self.released_languages.strip():
            return []

        languages = [lang.lower().strip() for lang in self.released_languages.split(',')]
        # Put in alphabetical order
        languages.sort()
        return languages

    @property
    def beta_languages_list(self):
        """
        ``released_languages`` as a list of language codes.

        Example: ['it', 'de-at', 'es', 'pt-br']
        """
        if not self.beta_languages.strip():
            return []

        languages = [lang.lower().strip() for lang in self.beta_languages.split(',')]
        # Put in alphabetical order
        languages.sort()
        return languages
