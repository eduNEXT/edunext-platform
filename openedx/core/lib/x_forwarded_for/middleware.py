"""
Middleware to adjust some request values to account for reverse proxies.
"""
import ipaddress
import warnings

from django.utils.deprecation import MiddlewareMixin
from edx_django_utils.monitoring import set_custom_attribute

import openedx.core.djangoapps.util.ip as ip


def _ip_type(ip_str):
    """
    Produce a short, approximate term describing the IP address type.
    """
    try:
        if ipaddress.ip_address(ip_str).is_global:
            # Globally routable IPs are what most people think of as
            # "public" IPs.
            return 'pub'
        else:
            # Anything else is "private", although it may actually be
            # link-local, multicast, etc. rather than a private-range
            # IP, per se.
            return 'priv'
    except ValueError:
        # Something unparseable.
        return 'unknown'


class XForwardedForMiddleware(MiddlewareMixin):
    """
    The middleware name is outdated, since it no longer uses a hardcoded reference
    to X-Forwarded-For.
    """

    def process_request(self, request):
        """
        Process the given request, update the value of SERVER_NAME and SERVER_PORT based
        on HTTP_HOST and X-Forwarded-Port headers that were set by some upstream proxy.
        """
        # Must be called before the REMOTE_ADDR override that happens below.
        # This function will cache its results in the request.
        ip.init_client_ips(request)

        # Only used to support ip.legacy switch.
        request.META['ORIGINAL_REMOTE_ADDR'] = request.META['REMOTE_ADDR']

        try:
            # Give some observability into IP chain length and composition. Useful
            # for monitoring in case of unexpected network config changes, etc.
            ip_chain = ip.get_raw_ip_chain(request)
            set_custom_attribute('ip_chain.count', len(ip_chain))
            set_custom_attribute('ip_chain.types', '-'.join(_ip_type(s) for s in ip_chain))

            set_custom_attribute('ip_chain.use_legacy', ip.USE_LEGACY_IP.is_enabled())

            external_chain = ip.get_all_client_ips(request)
            set_custom_attribute('ip_chain.external.count', len(external_chain))
            set_custom_attribute('ip_chain.external.types', '-'.join(_ip_type(s) for s in external_chain))
        except BaseException:
            warnings.warn('Error while computing IP chain metrics')

        # Older code for the Gunicorn 19.0 upgrade. Original docstring:
        #
        #    Gunicorn 19.0 has breaking changes for REMOTE_ADDR, SERVER_* headers
        #    that can not override with forwarded and host headers.
        #    This middleware can be used to update these headers set by proxy configuration.
        #
        # REMOTE_ADDR has since been removed from this override and is now
        # handled separately below.
        for field, header in [("HTTP_HOST", "SERVER_NAME"),
                              ("HTTP_X_FORWARDED_PORT", "SERVER_PORT")]:
            if field in request.META:
                request.META[header] = request.META[field]

        # This should eventually be deleted, but is here to avoid breaking
        # older code. This override was previously implemented in the above
        # code by using the first IP in X-Forwarded-For, and just overwrote
        # REMOTE_ADDR, which probably creates more problems elsewhere (as
        # the full IP chain is then no longer possible to construct.)
        #
        # The old code chose the leftmost IP in the external chain
        # (first in XFF) but now chooses the rightmost, which is the
        # safer choice when the specific needs of the relying code are
        # not known.
        #
        # Any code that is relying on this override should instead be
        # using the IP utility module used here, which is configurable and
        # makes it possible to handle multi-valued headers correctly.
        # After that, this override can probably be safely removed.
        #
        # It is very important that init_client_ips is called before this
        # point, allowing it to cache its results in request.META, since
        # after this point it will be more difficult for it to operate
        # without knowing about ORIGINAL_REMOTE_ADDR. (The less code that
        # is aware of that, the better, and the ip code should be lifted
        # out into a library anyhow.)
        if ip.USE_LEGACY_IP.is_enabled():
            request.META['REMOTE_ADDR'] = ip.get_legacy_ip(request)
        else:
            request.META['REMOTE_ADDR'] = ip.get_safest_client_ip(request)
