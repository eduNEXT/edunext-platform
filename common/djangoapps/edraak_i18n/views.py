from django.views.i18n import set_language as django_set_language
from django.views.decorators.csrf import csrf_exempt
from dark_lang import DARK_LANGUAGE_KEY
from django_locale.trans_real import LANGUAGE_SESSION_KEY
from openedx.core.djangoapps.user_api.preferences.api import set_user_preference
from django import http


@csrf_exempt
def set_language(request):

    auth_user = request.user.is_authenticated()
    lang_code = request.POST.get('language', None)

    request.session[LANGUAGE_SESSION_KEY] = lang_code

    if auth_user:
        set_user_preference(request.user, DARK_LANGUAGE_KEY, lang_code)

    return django_set_language(request)
    # we can return a simple redirect response, but I left this in place just in case !