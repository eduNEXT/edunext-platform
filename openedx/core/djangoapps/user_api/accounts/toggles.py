"""
Toggles for accounts related code.
"""

from edx_toggles.toggles import WaffleFlag

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

# .. toggle_name: order_history.redirect_to_microfrontend
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Supports staged rollout of a new micro-frontend-based implementation of the order history page.
# .. toggle_use_cases: temporary, open_edx
# .. toggle_creation_date: 2019-04-11
# .. toggle_target_removal_date: 2020-12-31
# .. toggle_warning: Also set settings.ORDER_HISTORY_MICROFRONTEND_URL and site's
#   ENABLE_ORDER_HISTORY_MICROFRONTEND.
# .. toggle_tickets: DEPR-17
REDIRECT_TO_ORDER_HISTORY_MICROFRONTEND = WaffleFlag('order_history.redirect_to_microfrontend', __name__)


def should_redirect_to_order_history_microfrontend():
    return (
        configuration_helpers.get_value('ENABLE_ORDER_HISTORY_MICROFRONTEND') and
        REDIRECT_TO_ORDER_HISTORY_MICROFRONTEND.is_enabled()
    )


def should_show_linked_accounts_tab():
    """Check if the the var `SHOW_LINKED_ACCOUNTS`
        is defined in configuration helpers.
    """
    return configuration_helpers.get_value('SHOW_LINKED_ACCOUNTS', True)


# .. toggle_name: account.redirect_to_microfrontend
# .. toggle_implementation: WaffleFlag
# .. toggle_default: False
# .. toggle_description: Supports staged rollout of a new micro-frontend-based implementation of the account page.
#   Its action can be overridden using site's ENABLE_ACCOUNT_MICROFRONTEND setting.
# .. toggle_use_cases: temporary, open_edx
# .. toggle_creation_date: 2019-04-30
# .. toggle_target_removal_date: 2021-12-31
# .. toggle_warning: Also set settings.ACCOUNT_MICROFRONTEND_URL.
# .. toggle_tickets: DEPR-17
REDIRECT_TO_ACCOUNT_MICROFRONTEND = WaffleFlag('account.redirect_to_microfrontend', __name__)


def should_redirect_to_account_microfrontend():
    return configuration_helpers.get_value('ENABLE_ACCOUNT_MICROFRONTEND',
                                           REDIRECT_TO_ACCOUNT_MICROFRONTEND.is_enabled())
