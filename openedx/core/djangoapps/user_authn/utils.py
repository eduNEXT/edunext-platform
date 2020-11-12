"""
Utility functions used during user authentication.
"""

import random
import string
from urllib.parse import urlparse  # pylint: disable=import-error

from django.conf import settings
from django.utils import http
from oauth2_provider.models import Application


def is_safe_login_or_logout_redirect(redirect_to, request_host, dot_client_id, require_https):
    """
    Determine if the given redirect URL/path is safe for redirection.

    Arguments:
        redirect_to (str):
            The URL in question.
        request_host (str):
            Originating hostname of the request.
            This is always considered an acceptable redirect target.
        dot_client_id (str|None):
            ID of Django OAuth Toolkit client.
            It is acceptable to redirect to any of the DOT client's redirct URIs.
            This argument is ignored if it is None.
        require_https (str):
            Whether HTTPs should be required in the redirect URL.

    Returns: bool
    """
    login_redirect_whitelist = set(getattr(settings, 'LOGIN_REDIRECT_WHITELIST', []))
    login_redirect_whitelist.add(request_host)

    # Allow OAuth2 clients to redirect back to their site after logout.
    if dot_client_id:
        application = Application.objects.get(client_id=dot_client_id)
        if redirect_to in application.redirect_uris:
            login_redirect_whitelist.add(urlparse(redirect_to).netloc)

    is_safe_url = http.is_safe_url(
        redirect_to, allowed_hosts=login_redirect_whitelist, require_https=require_https
    )
    return is_safe_url


def password_complexity():
    """
    Inspect AUTH_PASSWORD_VALIDATORS setting and generate a dict with the requirements for
    usage in the generate_password function
    """
    password_validators = settings.AUTH_PASSWORD_VALIDATORS
    known_validators = {
        "util.password_policy_validators.MinimumLengthValidator": "min_length",
        "util.password_policy_validators.MaximumLengthValidator": "max_length",
        "util.password_policy_validators.AlphabeticValidator": "min_alphabetic",
        "util.password_policy_validators.UppercaseValidator": "min_upper",
        "util.password_policy_validators.LowerValidator": "min_lower",
        "util.password_policy_validators.NumericValidator": "min_numeric",
        "util.password_policy_validators.PunctuationValidator": "min_punctuation",
        "util.password_policy_validators.SymbolValidator": "min_symbol",
    }
    complexity = {}

    for validator in password_validators:
        param_name = known_validators.get(validator["NAME"], None)
        if param_name is not None:
            complexity[param_name] = validator["OPTIONS"].get(param_name, 0)

    # merge alphabetic with lower and uppercase
    if complexity.get("min_alphabetic") and (
        complexity.get("min_lower") or complexity.get("min_upper")
    ):
        complexity["min_alphabetic"] = max(
            0,
            complexity["min_alphabetic"]
            - complexity.get("min_lower", 0)
            - complexity.get("min_upper", 0),
        )

    return complexity


def generate_password(length=12, chars=string.ascii_letters + string.digits):
    """Generate a valid random password"""
    if length < 8:
        raise ValueError("password must be at least 8 characters")

    password = ''
    choice = random.SystemRandom().choice
    non_ascii_characters = [
        '£',
        '¥',
        '€',
        '©',
        '®',
        '™',
        '†',
        '§',
        '¶',
        'π',
        'μ',
        '±',
    ]

    complexity = password_complexity()
    password_length = max(length, complexity.get('min_length'))

    password_rules = {
        'min_lower': list(string.ascii_lowercase),
        'min_upper': list(string.ascii_uppercase),
        'min_alphabetic': list(string.ascii_letters),
        'min_numeric': list(string.digits),
        'min_punctuation': list(string.punctuation),
        'min_symbol': list(non_ascii_characters),
    }

    for rule, elems in password_rules.items():
        needed = complexity.get(rule, 0)
        for _ in range(needed):
            next_char = choice(elems)
            password += next_char
            elems.remove(next_char)

    # fill the password to reach password_length
    if len(password) < password_length:
        password += ''.join(
            [choice(chars) for _ in range(password_length - len(password))]
        )

    password_list = list(password)
    random.shuffle(password_list)

    password = ''.join(password_list)
    return password


def is_registration_api_v1(request):
    """
    Checks if registration api is v1
    :param request:
    :return: Bool
    """
    return 'v1' in request.get_full_path() and 'register' not in request.get_full_path()
