"""
Utility functions used during user authentication.
"""

import random
import string

from urllib.parse import urlparse  # pylint: disable=import-error
from uuid import uuid4  # lint-amnesty, pylint: disable=unused-import

from django.conf import settings
from django.utils import http
from oauth2_provider.models import Application

from common.djangoapps.student.models import username_exists_or_retired
from openedx.core.djangoapps.user_api.accounts import USERNAME_MAX_LENGTH


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


def password_rules():
    """
    Inspect the validators defined in AUTH_PASSWORD_VALIDATORS and define
    a rule list with the set of available characters and their minimum
    for a specific charset category (alphabetic, digits, uppercase, etc).

    This is based on the validators defined in
    common.djangoapps.util.password_policy_validators and
    django_password_validators.password_character_requirements.password_validation.PasswordCharacterValidator
    """
    password_validators = settings.AUTH_PASSWORD_VALIDATORS
    rules = {
        "alpha": [string.ascii_letters, 0],
        "digit": [string.digits, 0],
        "upper": [string.ascii_uppercase, 0],
        "lower": [string.ascii_lowercase, 0],
        "punctuation": [string.punctuation, 0],
        "symbol": ["£¥€©®™†§¶πμ'±", 0],
        "min_length": ["", 0],
    }
    options_mapping = {
        "min_alphabetic": "alpha",
        "min_length_alpha": "alpha",
        "min_length_digit": "digit",
        "min_length_upper": "upper",
        "min_length_lower": "lower",
        "min_lower": "lower",
        "min_upper": "upper",
        "min_numeric": "digit",
        "min_symbol": "symbol",
        "min_punctuation": "punctuation",
    }

    for validator in password_validators:
        for option, mapping in options_mapping.items():
            if not validator.get("OPTIONS"):
                continue
            rules[mapping][1] = max(
                rules[mapping][1], validator["OPTIONS"].get(option, 0)
            )
        # We handle PasswordCharacterValidator separately because it can define
        # its own set of special characters.
        if (
            validator["NAME"] ==
            "django_password_validators.password_character_requirements.password_validation.PasswordCharacterValidator"
        ):
            min_special = validator["OPTIONS"].get("min_length_special", 0)
            special_chars = validator["OPTIONS"].get(
                "special_characters", "~!@#$%^&*()_+{}\":;'[]"
            )
            rules["special"] = [special_chars, min_special]

    return rules


def generate_password(length=12, chars=string.ascii_letters + string.digits):
    """Generate a valid random password.

    The original `generate_password` doesn't account for extra validators
    This picks the minimum amount of characters for each charset category.
    """
    if length < 8:
        raise ValueError("password must be at least 8 characters")

    password = ""
    password_length = length
    choice = random.SystemRandom().choice
    rules = password_rules()
    min_length = rules.pop("min_length")[1]
    password_length = max(min_length, length)

    for elems in rules.values():
        choices = elems[0]
        needed = elems[1]
        for _ in range(needed):
            next_char = choice(choices)
            password += next_char

    # fill the password to reach password_length
    if len(password) < password_length:
        password += "".join(
            [choice(chars) for _ in range(password_length - len(password))]
        )

    password_list = list(password)
    random.shuffle(password_list)

    password = "".join(password_list)
    return password


def is_registration_api_v1(request):
    """
    Checks if registration api is v1
    :param request:
    :return: Bool
    """
    return 'v1' in request.get_full_path() and 'register' not in request.get_full_path()


def generate_username_suggestions(username):
    """ Generate 3 available username suggestions """
    max_length = USERNAME_MAX_LENGTH
    short_username = username[:max_length - 6] if max_length is not None else username
    short_username = short_username.replace('_', '').replace('-', '')

    username_suggestions = []
    int_ranges = [
        {'min': 0, 'max': 9},
        {'min': 10, 'max': 99},
        {'min': 100, 'max': 999},
        {'min': 1000, 'max': 99999},
    ]
    for int_range in int_ranges:
        for _ in range(10):
            random_int = random.randint(int_range['min'], int_range['max'])
            suggestion = f'{short_username}_{random_int}'
            if not username_exists_or_retired(suggestion):
                username_suggestions.append(suggestion)
                break

        if len(username_suggestions) == 3:
            break

    return username_suggestions
