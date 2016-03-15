"""
Middleware for microsite redirections at edunext
"""
import re

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponseNotFound

import edxmako
from microsite_configuration import microsite
from models import Redirection


host_validation_re = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}(:[0-9]{2,5})?$")


class MicrositeMiddleware(object):
    """
    Middleware for Redirecting microsites to other domains or to error pages
    """

    def process_request(self, request):
        """
        This middleware handles redirections and error pages according to the
        business logic at edunext
        """
        domain = request.META.get('HTTP_HOST', None)

        # First handle the event where a domain has a redirect target
        # TODO: heavily use cache, we could even cache the result of a function and if it is none, just return
        try:
            target = Redirection.objects.get(domain__iexact=domain)
        except Redirection.DoesNotExist:
            target = None

        if target:
            # If we are already at the target, just return
            if domain == target.target and request.scheme == target.scheme:
                return

            to_url = '{scheme}://{host}{path}'.format(
                scheme=target.scheme,
                host=target.target,
                path=request.path,
            )

            return HttpResponseRedirect(
                to_url,
                status=target.status,
            )

        # By this time, if there is no redirect, and no microsite, the domain is available
        if (
           not microsite.is_request_in_microsite() and
           settings.FEATURES['USE_MICROSITE_AVAILABLE_SCREEN'] and
           not bool(host_validation_re.search(domain))
           ):
            return HttpResponseNotFound(edxmako.shortcuts.render_to_string('microsites/not_found.html', {
                'domain': domain,
            }))
