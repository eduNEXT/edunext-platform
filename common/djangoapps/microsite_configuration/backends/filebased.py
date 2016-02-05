"""
Microsite backend that reads the configuration from a file

"""
import os.path

from microsite_configuration.backends.base import (
    BaseMicrositeBackend,
    BaseMicrositeTemplateBackend,
)
from microsite_configuration.microsite import get_value as microsite_get_value


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

    def get_template_path(self, relative_path, **kwargs):
        """
        Returns a path (string) to a Mako template, which can either be in
        an override or will just return what is passed in which is expected to be a string
        """

        microsite_template_path = str(microsite_get_value('template_dir', None))

        if microsite_template_path:
            search_path = os.path.join(microsite_template_path, relative_path)

            if os.path.isfile(search_path):
                path = '/{0}/templates/{1}'.format(
                    microsite_get_value('microsite_name'),
                    relative_path
                )
                return path

        return relative_path
