"""
Models for the dark-launching languages
"""
from config_models.models import ConfigurationModel
from django.conf import settings
from django.db import models
from microsite_configuration import microsite


class DarkLangConfig(ConfigurationModel):
    """
    Configuration for the dark_lang django app.
    """
    released_languages = models.TextField(
        blank=True,
        help_text="A comma-separated list of language codes to release to the public."
    )

    def __unicode__(self):
        return u"DarkLangConfig()"

    @property
    def released_languages_list(self):
        """
        ``released_languages`` as a list of language codes.

        Example: ['it', 'de-at', 'es', 'pt-br']

        eduNEXT: we support only the list of available languages from the site
        otherwise is the same as having no configuration
        """
        if settings.FEATURES.get("EDNX_SITE_AWARE_LOCALE", False):
            site_released_langs = microsite.get_value("released_languages", [])
            if site_released_langs:
                site_released_langs = [lang.lower().strip() for lang in site_released_langs.split(',')]
                site_released_langs.sort()

            return site_released_langs

        languages = [lang.lower().strip() for lang in self.released_languages.split(',')]
        # Put in alphabetical order
        languages.sort()
        return languages
