"""
Helper methods for the CMS.
"""

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from edx_toggles.toggles import SettingDictToggle


def use_course_authoring_mfe(org) -> bool:
    """
    Checks with the org if the tenant enables the
    Course Authoring MFE.
    Returns:
        True if the MFE setting is activated, by default
        the MFE is deactivated
    """

    ENABLE_MFE_FOR_TESTING = SettingDictToggle(
        "FEATURES", "ENABLE_MFE_FOR_TESTING", default=False, module_name=__name__
    ).is_enabled()

    use_microfrontend = configuration_helpers.get_value_for_org(
        org, "ENABLE_COURSE_AUTHORING_MFE", ENABLE_MFE_FOR_TESTING or False
    )

    return bool(use_microfrontend)
