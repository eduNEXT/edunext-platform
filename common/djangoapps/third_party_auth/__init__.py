"""Third party authentication. """

from microsite_configuration import microsite


def is_enabled():
    """Check whether third party authentication has been enabled. """

    return microsite.get_value(
        "ENABLE_THIRD_PARTY_AUTH",
        False  # This forces the module to be enabled on a per microsite basis
    )
