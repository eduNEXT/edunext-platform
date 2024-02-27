"""Third party authentication. """


from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

default_app_config = 'common.djangoapps.third_party_auth.apps.ThirdPartyAuthConfig'


def is_enabled():
    """Check whether third party authentication has been enabled. """

    # We do this import internally to avoid initializing settings prematurely
    from django.conf import settings

    return configuration_helpers.get_value(
        "ENABLE_THIRD_PARTY_AUTH",
        # This forces the module to be enabled on a per tenant basis
        settings.FEATURES.get("ENABLE_THIRD_PARTY_AUTH_FOR_TEST", False)
    )
