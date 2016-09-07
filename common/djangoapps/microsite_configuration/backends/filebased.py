"""
Microsite backend that reads the configuration from a file

"""
import os.path

from django.conf import settings

from microsite_configuration.backends.base import (
    BaseMicrositeBackend,
    BaseMicrositeTemplateBackend,
)
from microsite_configuration.microsite import get_value as microsite_get_value
from microsite_configuration.microsite import is_request_in_microsite


class FilebasedMicrositeBackend(BaseMicrositeBackend):
    """
    Microsite backend that reads the microsites definitions
    from a dictionary called MICROSITE_CONFIGURATION in the settings file.
    """

    def __init__(self, **kwargs):
        super(FilebasedMicrositeBackend, self).__init__(**kwargs)


class FilebasedMicrositeTemplateBackend(BaseMicrositeTemplateBackend):
    """
    Microsite backend that loads templates from filesystem.
    """
    pass


class EdunextCompatibleFilebasedMicrositeTemplateBackend(FilebasedMicrositeTemplateBackend):
    """
    Microsite backend that loads templates from filesystem using the configuration
    held before dogwood by edunext
    """
    def make_absolute_path(self, relative_path):
        return '/' + relative_path

    def get_template_path(self, relative_path, **kwargs):
        """
        Returns a path (string) to a Mako template, which can either be in
        an override or will just return what is passed in which is expected to be a string
        """

        leading_slash = kwargs.get('leading_slash', False)

        if not is_request_in_microsite():
            return '/' + relative_path if leading_slash else relative_path

        template_dir = str(microsite_get_value('template_dir', microsite_get_value('microsite_name')))

        if template_dir:
            search_path = os.path.join(
                settings.MICROSITE_ROOT_DIR,
                template_dir,
                'templates',
                relative_path
            )

            if os.path.isfile(search_path):
                path = '{0}/templates/{1}'.format(
                    template_dir,
                    relative_path
                )
                return '/' + path if leading_slash else path

        return '/' + relative_path if leading_slash else relative_path
