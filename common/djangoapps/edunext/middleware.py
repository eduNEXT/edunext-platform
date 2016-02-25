"""
Middleware for Language Preferences
"""

from django.http import HttpResponseRedirect


class RedirectMiddleware(object):
    """
    Middleware for Redirecting microsites
    """

    def process_request(self, request):
        """
        Redirect if domain in redirect list
        """
        # TODO discuss how and from where this redirect should work, new table? microsites table? sites table?
        return HttpResponseRedirect('http://www.edunext.co')

