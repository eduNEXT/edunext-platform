"""
This file implements the Middleware support for the Open edX platform.
A microsite enables the following features:

1) Mapping of sub-domain name to a 'brand', e.g. foo-university.edx.org
2) Present a landing page with a listing of courses that are specific to the 'brand'
3) Ability to swap out some branding elements in the website
"""
from django.conf import settings
from django.http import Http404

from opaque_keys.edx.keys import CourseKey
from microsite_configuration import microsite
from certificates.models import GeneratedCertificate


class MicrositeMiddleware(object):
    """
    Middleware class which will bind configuration information regarding 'microsites' on a per request basis.
    The actual configuration information is taken from Django settings information
    """

    def process_request(self, request):
        """
        Middleware entry point on every request processing. This will associate a request's domain name
        with a 'University' and any corresponding microsite configuration information
        """
        microsite.clear()

        domain = request.META.get('HTTP_HOST', None)

        microsite.set_by_domain(domain)

        return None

    def process_response(self, request, response):
        """
        Middleware entry point for request completion.
        """
        microsite.clear()
        return response


class MicrositeSessionCookieDomainMiddleware(object):
    """
    Special case middleware which should be at the very end of the MIDDLEWARE list (so that it runs first
    on the process_response chain). This middleware will define a wrapper function for the set_cookie() function
    on the HttpResponse object, if the request is running in a middleware.

    This wrapped set_cookie will change the SESSION_COOKIE_DOMAIN setting so that the cookie can be bound to a
    fully customized URL.
    """

    def process_response(self, request, response):
        """
        Standard Middleware entry point
        """

        # See if we are running in a Microsite *AND* we have a custom SESSION_COOKIE_DOMAIN defined
        # in configuration
        if microsite.has_override_value('SESSION_COOKIE_DOMAIN'):

            # define wrapper function for the standard set_cookie()
            def _set_cookie_wrapper(key, value='', max_age=None, expires=None, path='/', domain=None, secure=None, httponly=False):

                # only override if we are setting the cookie name to be the one the Django Session Middleware uses
                # as defined in settings.SESSION_COOKIE_NAME
                if key == settings.SESSION_COOKIE_NAME:
                    domain = microsite.get_value('SESSION_COOKIE_DOMAIN', domain)

                # then call down into the normal Django set_cookie method
                return response.set_cookie_wrapped_func(
                    key,
                    value,
                    max_age=max_age,
                    expires=expires,
                    path=path,
                    domain=domain,
                    secure=secure,
                    httponly=httponly
                )

            # then point the HttpResponse.set_cookie to point to the wrapper and keep
            # the original around
            response.set_cookie_wrapped_func = response.set_cookie
            response.set_cookie = _set_cookie_wrapper

        return response


class MicrositeCrossBrandingFilterMiddleware():
    """
    Middleware class that prevents a course defined in a branded ORG trough a microsite, to be displayed
    on a different microsite with a different branding.
    """
    def process_request(self, request):
        """
        Raise an 404 exception if the page being rendered belongs to an ORG in a
        microsite, but it is not the current microsite
        """
        path = request.path_info

        for key, regex in settings.MICROSITE_CBFR.iteritems():
            match = regex.match(path)
            if match:
                filter_method = getattr(self, "clean_{}".format(key))
                return filter_method(match, request)

        # If there is no match, then we are not in a ORG-restricted area
        return None

    def match_org_or_404(self, org):
        """
        Checks the current microsite for the org and compares it to the input
        if the org is not included in the site, raises 404
        """
        org_filter = microsite.get_value('course_org_filter', set([]))
        if isinstance(org_filter, basestring):
            org_filter = set([org_filter])
        if org in org_filter:
            return None

        # If the course does not belong to an ORG defined in a microsite
        all_orgs = microsite.get_all_orgs()
        if org not in all_orgs:
            return None

        # We could log some of the output here for forensic analysis
        raise Http404

    def clean_courses(self, match, request):
        """
        Raise an 404 exception the course matched does not belong to the current org
        """
        course_id = match.group('course_id')
        course_key = CourseKey.from_string(course_id)
        return self.match_org_or_404(course_key.org)

    def clean_certs(self, match, request):
        """
        Raise an 404 exception the cert matched does not belong to the current org
        """
        uuid = match.group('certificate_uuid')

        try:
            certificate = GeneratedCertificate.objects.get(
                verify_uuid=uuid,
            )

            return self.match_org_or_404(certificate.course_id.org)
        except GeneratedCertificate.DoesNotExist:
            return None
