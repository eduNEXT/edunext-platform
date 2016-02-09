from django.views.i18n import set_language as django_set_language
from django.views.decorators.csrf import csrf_exempt
from dark_lang import DARK_LANGUAGE_KEY
from django.utils.translation.trans_real import LANGUAGE_SESSION_KEY
from openedx.core.djangoapps.user_api.preferences.api import set_user_preference
from django import http
from microsite_aware_functions.language import ma_language
from django.core.exceptions import PermissionDenied


@csrf_exempt
def set_language(request):
    auth_user = request.user.is_authenticated()
    lang_code = request.POST.get('language', None)
    if lang_code != ma_language(lang_code):
        # Trying to change to a non released language, ignore request.
        raise PermissionDenied
    request.session[LANGUAGE_SESSION_KEY] = lang_code

    if auth_user:
        set_user_preference(request.user, DARK_LANGUAGE_KEY, lang_code)

    return django_set_language(request)
    # we can return a simple redirect response, but I left this in place just in case !
