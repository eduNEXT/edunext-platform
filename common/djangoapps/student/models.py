"""
Models for User Information (students, staff, etc)

Migration Notes

If you make changes to this model, be sure to create an appropriate migration
file and check it in at the same time as your model changes. To do that,

1. Go to the edx-platform dir
2. ./manage.py lms schemamigration student --auto description_of_your_change
3. Add the migration file created in edx-platform/common/djangoapps/student/migrations/
"""


import crum
import hashlib  # lint-amnesty, pylint: disable=wrong-import-order
import json  # lint-amnesty, pylint: disable=wrong-import-order
import logging  # lint-amnesty, pylint: disable=wrong-import-order
import uuid  # lint-amnesty, pylint: disable=wrong-import-order
from collections import defaultdict, namedtuple  # lint-amnesty, pylint: disable=wrong-import-order
from datetime import date, datetime, timedelta  # lint-amnesty, pylint: disable=wrong-import-order
from functools import total_ordering  # lint-amnesty, pylint: disable=wrong-import-order
from importlib import import_module  # lint-amnesty, pylint: disable=wrong-import-order
from urllib.parse import urlencode  # lint-amnesty, pylint: disable=wrong-import-order
import warnings  # lint-amnesty, pylint: disable=wrong-import-order

from config_models.models import ConfigurationModel
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User  # lint-amnesty, pylint: disable=imported-auth-user
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import IntegrityError, models
from django.db.models import Count, Index, Q
from django.db.models.signals import post_save, pre_save
from django.db.utils import ProgrammingError
from django.dispatch import receiver

from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop
from django_countries.fields import CountryField
from edx_django_utils.cache import RequestCache, TieredCache, get_cache_key
from edx_django_utils import monitoring
from edx_rest_api_client.exceptions import SlumberBaseException
from eventtracking import tracker
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField, LearningContextKeyField
from opaque_keys.edx.keys import CourseKey
from pytz import UTC, timezone
from simple_history.models import HistoricalRecords
from slumber.exceptions import HttpClientError, HttpServerError
from user_util import user_util

from openedx_events.learning.data import (
    CourseData,
    CourseEnrollmentData,
    UserData,
    UserPersonalData,
)
from openedx_events.learning.signals import (
    COURSE_ENROLLMENT_CHANGED,
    COURSE_ENROLLMENT_CREATED,
    COURSE_UNENROLLMENT_COMPLETED,
)
from openedx_filters.learning.filters import CourseEnrollmentStarted, CourseUnenrollmentStarted
import openedx.core.djangoapps.django_comment_common.comment_client as cc
from common.djangoapps.course_modes.models import CourseMode, get_cosmetic_verified_display_price
from common.djangoapps.student.emails import send_proctoring_requirements_email
from common.djangoapps.student.email_helpers import (
    generate_proctoring_requirements_email_context,
    should_send_proctoring_requirements_email
)
from common.djangoapps.student.signals import ENROLL_STATUS_CHANGE, ENROLLMENT_TRACK_UPDATED, UNENROLL_DONE
from common.djangoapps.track import contexts, segment
from common.djangoapps.util.model_utils import emit_field_changed_events, get_changed_fields_dict
from common.djangoapps.util.query import use_read_replica_if_available
from lms.djangoapps.certificates.data import CertificateStatuses
from lms.djangoapps.courseware.models import (
    CourseDynamicUpgradeDeadlineConfiguration,
    DynamicUpgradeDeadlineConfiguration,
    OrgDynamicUpgradeDeadlineConfiguration,
)
from lms.djangoapps.courseware.toggles import streak_celebration_is_active
from lms.djangoapps.verify_student.models import SoftwareSecurePhotoVerification
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.enrollments.api import (
    _default_course_mode,
    get_enrollment_attributes,
    set_enrollment_attributes,
)
from openedx.core.djangoapps.signals.signals import USER_ACCOUNT_ACTIVATED
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.xmodule_django.models import NoneToEmptyManager
from openedx.core.djangolib.model_mixins import DeletableByUserValue
from openedx.core.toggles import ENTRANCE_EXAMS

log = logging.getLogger(__name__)
AUDIT_LOG = logging.getLogger("audit")
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore  # pylint: disable=invalid-name


# ENROLL signal used for free enrollment only
class EnrollStatusChange:
    """
    Possible event types for ENROLL_STATUS_CHANGE signal
    """
    # enroll for a course
    enroll = 'enroll'
    # unenroll for a course
    unenroll = 'unenroll'
    # add an upgrade to cart
    upgrade_start = 'upgrade_start'
    # complete an upgrade purchase
    upgrade_complete = 'upgrade_complete'
    # add a paid course to the cart
    paid_start = 'paid_start'
    # complete a paid course purchase
    paid_complete = 'paid_complete'

UNENROLLED_TO_ALLOWEDTOENROLL = 'from unenrolled to allowed to enroll'
ALLOWEDTOENROLL_TO_ENROLLED = 'from allowed to enroll to enrolled'
ENROLLED_TO_ENROLLED = 'from enrolled to enrolled'
ENROLLED_TO_UNENROLLED = 'from enrolled to unenrolled'
UNENROLLED_TO_ENROLLED = 'from unenrolled to enrolled'
ALLOWEDTOENROLL_TO_UNENROLLED = 'from allowed to enroll to enrolled'
UNENROLLED_TO_UNENROLLED = 'from unenrolled to unenrolled'
DEFAULT_TRANSITION_STATE = 'N/A'
SCORE_RECALCULATION_DELAY_ON_ENROLLMENT_UPDATE = 30

TRANSITION_STATES = (
    (UNENROLLED_TO_ALLOWEDTOENROLL, UNENROLLED_TO_ALLOWEDTOENROLL),
    (ALLOWEDTOENROLL_TO_ENROLLED, ALLOWEDTOENROLL_TO_ENROLLED),
    (ENROLLED_TO_ENROLLED, ENROLLED_TO_ENROLLED),
    (ENROLLED_TO_UNENROLLED, ENROLLED_TO_UNENROLLED),
    (UNENROLLED_TO_ENROLLED, UNENROLLED_TO_ENROLLED),
    (ALLOWEDTOENROLL_TO_UNENROLLED, ALLOWEDTOENROLL_TO_UNENROLLED),
    (UNENROLLED_TO_UNENROLLED, UNENROLLED_TO_UNENROLLED),
    (DEFAULT_TRANSITION_STATE, DEFAULT_TRANSITION_STATE)
)


class AnonymousUserId(models.Model):
    """
    This table contains user, course_Id and anonymous_user_id

    Purpose of this table is to provide user by anonymous_user_id.

    We generate anonymous_user_id using md5 algorithm,
    and use result in hex form, so its length is equal to 32 bytes.

    .. no_pii: We store anonymous_user_ids here, but do not consider them PII under OEP-30.
    """

    objects = NoneToEmptyManager()

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    anonymous_user_id = models.CharField(unique=True, max_length=32)
    course_id = LearningContextKeyField(db_index=True, max_length=255, blank=True)


def anonymous_id_for_user(user, course_id, save='DEPRECATED'):
    """
    Inputs:
        user: User model
        course_id: string or None
        save: Deprecated and ignored: ID is always saved in an AnonymousUserId object

    Return a unique id for a (user, course_id) pair, suitable for inserting
    into e.g. personalized survey links.

    If user is an `AnonymousUser`, returns `None`
    else If this user/course_id pair already has an anonymous id in AnonymousUserId object, return that
    else: create new anonymous_id, save it in AnonymousUserId, and return anonymous id
    """

    # This part is for ability to get xblock instance in xblock_noauth handlers, where user is unauthenticated.
    assert user

    if save != 'DEPRECATED':
        warnings.warn(
            "anonymous_id_for_user no longer accepts save param and now "
            "always saves the ID in the database",
            DeprecationWarning
        )

    if user.is_anonymous:
        return None

    # ARCHBOM-1674: Get a sense of what fraction of anonymous_user_id calls are
    # cached, stored in the DB, or retrieved from the DB. This will help inform
    # us on decisions about whether we can
    # pregenerate IDs, use random instead of deterministic IDs, etc.
    monitoring.increment('temp_anon_uid_v2.requested')

    cached_id = getattr(user, '_anonymous_id', {}).get(course_id)
    if cached_id is not None:
        monitoring.increment('temp_anon_uid_v2.returned_from_cache')
        return cached_id
    # Check if an anonymous id already exists for this user and
    # course_id combination. Prefer the one with the highest record ID
    # (see below.)
    anonymous_user_ids = AnonymousUserId.objects.filter(user=user).filter(course_id=course_id).order_by('-id')
    if anonymous_user_ids:
        # If there are multiple anonymous_user_ids per user, course_id pair
        # select the row which was created most recently.
        # There might be more than one if the Django SECRET_KEY had
        # previously been rotated at a time before this function was
        # changed to always save the generated IDs to the DB. In that
        # case, just pick the one with the highest record ID, which is
        # probably the most recently created one.
        anonymous_user_id = anonymous_user_ids[0].anonymous_user_id
        monitoring.increment('temp_anon_uid_v2.fetched_existing')
    else:
        # Uses SECRET_KEY as a cryptographic pepper. This
        # deterministic ID generation means that concurrent identical
        # calls to this function return the same value -- no need for
        # locking. (There may be a low level of integrity errors on
        # creation as a result of concurrent duplicate row inserts.)
        #
        # Consequences for this function of SECRET_KEY exposure: Data
        # researchers and other third parties receiving these
        # anonymous user IDs would be able to identify users across
        # courses, and predict the anonymous user IDs of all users
        # (but not necessarily identify their accounts.)
        #
        # Rotation process of SECRET_KEY with respect to this
        # function: Rotate at will, since the hashes are stored and
        # will not change.
        # include the secret key as a salt, and to make the ids unique across different LMS installs.
        hasher = hashlib.shake_128()
        hasher.update(settings.SECRET_KEY.encode('utf8'))
        hasher.update(str(user.id).encode('utf8'))
        if course_id:
            hasher.update(str(course_id).encode('utf-8'))
        anonymous_user_id = hasher.hexdigest(16)  # pylint: disable=too-many-function-args

        try:
            AnonymousUserId.objects.create(
                user=user,
                course_id=course_id,
                anonymous_user_id=anonymous_user_id,
            )
            monitoring.increment('temp_anon_uid_v2.stored')
        except IntegrityError:
            # Another thread has already created this entry, so
            # continue
            monitoring.increment('temp_anon_uid_v2.store_db_error')

    # cache the anonymous_id in the user object
    if not hasattr(user, '_anonymous_id'):
        user._anonymous_id = {}  # pylint: disable=protected-access
    user._anonymous_id[course_id] = anonymous_user_id  # pylint: disable=protected-access

    return anonymous_user_id


def user_by_anonymous_id(uid):
    """
    Return user by anonymous_user_id using AnonymousUserId lookup table.

    Do not raise `django.ObjectDoesNotExist` exception,
    if there is no user for anonymous_student_id,
    because this function will be used inside xmodule w/o django access.
    """

    if uid is None:
        return None

    request_cache = RequestCache('user_by_anonymous_id')
    cache_response = request_cache.get_cached_response(uid)
    if cache_response.is_found:
        return cache_response.value

    try:
        user = User.objects.get(anonymoususerid__anonymous_user_id=uid)
        request_cache.set(uid, user)
        return user
    except ObjectDoesNotExist:
        request_cache.set(uid, None)
        return None


def is_username_retired(username):
    """
    Checks to see if the given username has been previously retired
    """
    locally_hashed_usernames = user_util.get_all_retired_usernames(
        username,
        settings.RETIRED_USER_SALTS,
        settings.RETIRED_USERNAME_FMT
    )

    # TODO: Revert to this after username capitalization issues detailed in
    # PLAT-2276, PLAT-2277, PLAT-2278 are sorted out:
    # return User.objects.filter(username__in=list(locally_hashed_usernames)).exists()

    # Avoid circular import issues
    from openedx.core.djangoapps.user_api.models import UserRetirementStatus

    # Sandbox clean builds attempt to create users during migrations, before the database
    # is stable so UserRetirementStatus may not exist yet. This workaround can also go
    # when we are done with the username updates.
    try:
        return User.objects.filter(username__in=list(locally_hashed_usernames)).exists() or \
            UserRetirementStatus.objects.filter(original_username=username).exists()
    except ProgrammingError as exc:
        # Check the error message to make sure it's what we expect
        if "user_api_userretirementstatus" in str(exc):
            return User.objects.filter(username__in=list(locally_hashed_usernames)).exists()
        raise


def username_exists_or_retired(username):
    """
    Check a username for existence -or- retirement against the User model.
    """
    return User.objects.filter(username=username).exists() or is_username_retired(username)


def is_email_retired(email):
    """
    Checks to see if the given email has been previously retired
    """
    locally_hashed_emails = user_util.get_all_retired_emails(
        email,
        settings.RETIRED_USER_SALTS,
        settings.RETIRED_EMAIL_FMT
    )

    return User.objects.filter(email__in=list(locally_hashed_emails)).exists()


def email_exists_or_retired(email):
    """
    Check an email against the User model for existence.
    """
    return (
        User.objects.filter(email=email).exists() or
        is_email_retired(email) or
        AccountRecovery.objects.filter(secondary_email=email).exists()
    )


def get_retired_username_by_username(username):
    """
    If a UserRetirementStatus object with an original_username matching the given username exists,
    returns that UserRetirementStatus.retired_username value.  Otherwise, returns a "retired username"
    hashed using the newest configured salt.
    """
    UserRetirementStatus = apps.get_model('user_api', 'UserRetirementStatus')
    try:
        status = UserRetirementStatus.objects.filter(original_username=username).order_by('-modified').first()
        if status:
            return status.retired_username
    except UserRetirementStatus.DoesNotExist:
        pass
    return user_util.get_retired_username(username, settings.RETIRED_USER_SALTS, settings.RETIRED_USERNAME_FMT)


def get_retired_email_by_email(email):
    """
    If a UserRetirementStatus object with an original_email matching the given email exists,
    returns that UserRetirementStatus.retired_email value.  Otherwise, returns a "retired email"
    hashed using the newest configured salt.
    """
    UserRetirementStatus = apps.get_model('user_api', 'UserRetirementStatus')
    try:
        status = UserRetirementStatus.objects.filter(original_email=email).order_by('-modified').first()
        if status:
            return status.retired_email
    except UserRetirementStatus.DoesNotExist:
        pass
    return user_util.get_retired_email(email, settings.RETIRED_USER_SALTS, settings.RETIRED_EMAIL_FMT)


def _get_all_retired_usernames_by_username(username):
    """
    Returns a generator of "retired usernames", one hashed with each
    configured salt. Used for finding out if the given username has
    ever been used and retired.
    """
    return user_util.get_all_retired_usernames(username, settings.RETIRED_USER_SALTS, settings.RETIRED_USERNAME_FMT)


def _get_all_retired_emails_by_email(email):
    """
    Returns a generator of "retired emails", one hashed with each
    configured salt. Used for finding out if the given email has
    ever been used and retired.
    """
    return user_util.get_all_retired_emails(email, settings.RETIRED_USER_SALTS, settings.RETIRED_EMAIL_FMT)


def get_potentially_retired_user_by_username(username):
    """
    Attempt to return a User object based on the username, or if it
    does not exist, then any hashed username salted with the historical
    salts.
    """
    locally_hashed_usernames = list(_get_all_retired_usernames_by_username(username))
    locally_hashed_usernames.append(username)
    potential_users = User.objects.filter(username__in=locally_hashed_usernames)

    # Have to disambiguate between several Users here as we could have retirees with
    # the same username, but for case.
    # If there's only 1 we're done, this should be the common case
    if len(potential_users) == 1:
        return potential_users[0]

    # No user found, throw the usual error
    if not potential_users:
        raise User.DoesNotExist()

    # For a brief period, users were able to retire accounts and make another account with
    # the same differently-cased username, like "testuser" and "TestUser".
    # If there are two users found, return the one that's the *actual* case-matching username,
    # whether retired or not.
    if len(potential_users) == 2:
        # Figure out which user has been retired.
        if potential_users[0].username.startswith(settings.RETIRED_USERNAME_PREFIX):
            retired = potential_users[0]
            active = potential_users[1]
        else:
            retired = potential_users[1]
            active = potential_users[0]

        # If the active (non-retired) user's username doesn't *exactly* match (including case),
        # then the retired account must be the one that exactly matches.
        return active if active.username == username else retired

    # We should have, at most, a retired username and an active one with a username
    # differing only by case. If there are more we need to disambiguate them by hand.
    raise Exception(f'Expected 1 or 2 Users, received {str(potential_users)}')


def get_potentially_retired_user_by_username_and_hash(username, hashed_username):
    """
    To assist in the retirement process this method will:
    - Confirm that any locally hashed username matches the passed in one
      (in case of salt mismatches with the upstream script).
    - Attempt to return a User object based on the username, or if it
      does not exist, the any hashed username salted with the historical
      salts.
    """
    locally_hashed_usernames = list(_get_all_retired_usernames_by_username(username))

    if hashed_username not in locally_hashed_usernames:
        raise Exception('Mismatched hashed_username, bad salt?')

    locally_hashed_usernames.append(username)
    return User.objects.get(username__in=locally_hashed_usernames)


class UserStanding(models.Model):
    """
    This table contains a student's account's status.
    Currently, we're only disabling accounts; in the future we can imagine
    taking away more specific privileges, like forums access, or adding
    more specific karma levels or probationary stages.

    .. no_pii:
    """
    ACCOUNT_DISABLED = "disabled"
    ACCOUNT_ENABLED = "enabled"
    USER_STANDING_CHOICES = (
        (ACCOUNT_DISABLED, "Account Disabled"),
        (ACCOUNT_ENABLED, "Account Enabled"),
    )

    user = models.OneToOneField(User, db_index=True, related_name='standing', on_delete=models.CASCADE)
    account_status = models.CharField(
        blank=True, max_length=31, choices=USER_STANDING_CHOICES
    )
    changed_by = models.ForeignKey(User, blank=True, on_delete=models.CASCADE)
    standing_last_changed_at = models.DateTimeField(auto_now=True)


class UserProfile(models.Model):
    """This is where we store all the user demographic fields. We have a
    separate table for this rather than extending the built-in Django auth_user.

    Notes:
        * Some fields are legacy ones from the first run of 6.002, from which
          we imported many users.
        * Fields like name and address are intentionally open ended, to account
          for international variations. An unfortunate side-effect is that we
          cannot efficiently sort on last names for instance.

    Replication:
        * Only the Portal servers should ever modify this information.
        * All fields are replicated into relevant Course databases

    Some of the fields are legacy ones that were captured during the initial
    MITx fall prototype.

    .. pii: Contains many PII fields. Retired in AccountRetirementView.
    .. pii_types: name, location, birth_date, gender, biography, phone_number
    .. pii_retirement: local_api
    """
    # cache key format e.g user.<user_id>.profile.country = 'SG'
    PROFILE_COUNTRY_CACHE_KEY = "user.{user_id}.profile.country"

    class Meta:
        db_table = "auth_userprofile"
        permissions = (("can_deactivate_users", "Can deactivate, but NOT delete users"),)

    # CRITICAL TODO/SECURITY
    # Sanitize all fields.
    # This is not visible to other users, but could introduce holes later
    user = models.OneToOneField(User, unique=True, db_index=True, related_name='profile', on_delete=models.CASCADE)
    name = models.CharField(blank=True, max_length=255, db_index=True)

    meta = models.TextField(blank=True)  # JSON dictionary for future expansion
    courseware = models.CharField(blank=True, max_length=255, default='course.xml')

    # Language is deprecated and no longer used. Old rows exist that have
    # user-entered free form text values (ex. "English"), some of which have
    # non-ASCII values. You probably want UserPreference version of this, which
    # stores the user's preferred language code. See openedx/core/djangoapps/lang_pref
    # for more information.
    language = models.CharField(blank=True, max_length=255, db_index=True)

    # Location is no longer used, but is held here for backwards compatibility
    # for users imported from our first class.
    location = models.CharField(blank=True, max_length=255, db_index=True)

    # Optional demographic data we started capturing from Fall 2012
    this_year = datetime.now(UTC).year
    VALID_YEARS = range(this_year - 16, this_year - 120, -1)
    year_of_birth = models.IntegerField(blank=True, null=True, db_index=True)
    GENDER_CHOICES = (
        ('m', gettext_noop('Male')),
        ('f', gettext_noop('Female')),
        # Translators: 'Other' refers to the student's gender
        ('o', gettext_noop('Other/Prefer Not to Say'))
    )
    gender = models.CharField(
        blank=True, null=True, max_length=6, db_index=True, choices=GENDER_CHOICES
    )

    # [03/21/2013] removed these, but leaving comment since there'll still be
    # p_se and p_oth in the existing data in db.
    # ('p_se', 'Doctorate in science or engineering'),
    # ('p_oth', 'Doctorate in another field'),
    LEVEL_OF_EDUCATION_CHOICES = (
        ('p', gettext_noop('Doctorate')),
        ('m', gettext_noop("Master's or professional degree")),
        ('b', gettext_noop("Bachelor's degree")),
        ('a', gettext_noop("Associate degree")),
        ('hs', gettext_noop("Secondary/high school")),
        ('jhs', gettext_noop("Junior secondary/junior high/middle school")),
        ('el', gettext_noop("Elementary/primary school")),
        # Translators: 'None' refers to the student's level of education
        ('none', gettext_noop("No formal education")),
        # Translators: 'Other' refers to the student's level of education
        ('other', gettext_noop("Other education"))
    )
    level_of_education = models.CharField(
        blank=True, null=True, max_length=6, db_index=True,
        choices=LEVEL_OF_EDUCATION_CHOICES
    )
    mailing_address = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    country = CountryField(blank=True, null=True)
    COUNTRY_WITH_STATES = 'US'
    STATE_CHOICES = (
        ('AL', 'Alabama'),
        ('AK', 'Alaska'),
        ('AZ', 'Arizona'),
        ('AR', 'Arkansas'),
        ('AA', 'Armed Forces Americas'),
        ('AE', 'Armed Forces Europe'),
        ('AP', 'Armed Forces Pacific'),
        ('CA', 'California'),
        ('CO', 'Colorado'),
        ('CT', 'Connecticut'),
        ('DE', 'Delaware'),
        ('DC', 'District Of Columbia'),
        ('FL', 'Florida'),
        ('GA', 'Georgia'),
        ('HI', 'Hawaii'),
        ('ID', 'Idaho'),
        ('IL', 'Illinois'),
        ('IN', 'Indiana'),
        ('IA', 'Iowa'),
        ('KS', 'Kansas'),
        ('KY', 'Kentucky'),
        ('LA', 'Louisiana'),
        ('ME', 'Maine'),
        ('MD', 'Maryland'),
        ('MA', 'Massachusetts'),
        ('MI', 'Michigan'),
        ('MN', 'Minnesota'),
        ('MS', 'Mississippi'),
        ('MO', 'Missouri'),
        ('MT', 'Montana'),
        ('NE', 'Nebraska'),
        ('NV', 'Nevada'),
        ('NH', 'New Hampshire'),
        ('NJ', 'New Jersey'),
        ('NM', 'New Mexico'),
        ('NY', 'New York'),
        ('NC', 'North Carolina'),
        ('ND', 'North Dakota'),
        ('OH', 'Ohio'),
        ('OK', 'Oklahoma'),
        ('OR', 'Oregon'),
        ('PA', 'Pennsylvania'),
        ('RI', 'Rhode Island'),
        ('SC', 'South Carolina'),
        ('SD', 'South Dakota'),
        ('TN', 'Tennessee'),
        ('TX', 'Texas'),
        ('UT', 'Utah'),
        ('VT', 'Vermont'),
        ('VA', 'Virginia'),
        ('WA', 'Washington'),
        ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'),
        ('WY', 'Wyoming'),
    )
    state = models.CharField(blank=True, null=True, max_length=2, choices=STATE_CHOICES)
    goals = models.TextField(blank=True, null=True)
    bio = models.CharField(blank=True, null=True, max_length=3000, db_index=False)
    profile_image_uploaded_at = models.DateTimeField(null=True, blank=True)
    phone_regex = RegexValidator(regex=r'^\+?1?\d*$', message="Phone number can only contain numbers.")
    phone_number = models.CharField(validators=[phone_regex], blank=True, null=True, max_length=50)

    @property
    def has_profile_image(self):
        """
        Convenience method that returns a boolean indicating whether or not
        this user has uploaded a profile image.
        """
        return self.profile_image_uploaded_at is not None

    @property
    def age(self):
        """ Convenience method that returns the age given a year_of_birth. """
        year_of_birth = self.year_of_birth
        year = datetime.now(UTC).year
        if year_of_birth is not None:
            return self._calculate_age(year, year_of_birth)

    @property
    def level_of_education_display(self):
        """ Convenience method that returns the human readable level of education. """
        if self.level_of_education:
            return self.__enumerable_to_display(self.LEVEL_OF_EDUCATION_CHOICES, self.level_of_education)

    @property
    def gender_display(self):
        """ Convenience method that returns the human readable gender. """
        if self.gender:
            return self.__enumerable_to_display(self.GENDER_CHOICES, self.gender)

    def get_meta(self):  # pylint: disable=missing-function-docstring
        js_str = self.meta
        if not js_str:
            js_str = {}
        else:
            js_str = json.loads(self.meta)

        return js_str

    def set_meta(self, meta_json):
        self.meta = json.dumps(meta_json)

    def set_login_session(self, session_id=None):
        """
        Sets the current session id for the logged-in user.
        If session_id doesn't match the existing session,
        deletes the old session object.
        """
        meta = self.get_meta()
        old_login = meta.get('session_id', None)
        if old_login:
            SessionStore(session_key=old_login).delete()
        meta['session_id'] = session_id
        self.set_meta(meta)
        self.save()

    def requires_parental_consent(self, year=None, age_limit=None, default_requires_consent=True):
        """Returns true if this user requires parental consent.

        Args:
            year (int): The year for which consent needs to be tested (defaults to now).
            age_limit (int): The age limit at which parental consent is no longer required.
                This defaults to the value of the setting 'PARENTAL_CONTROL_AGE_LIMIT'.
            default_requires_consent (bool): True if users require parental consent if they
                have no specified year of birth (default is True).

        Returns:
             True if the user requires parental consent.
        """
        if age_limit is None:
            age_limit = getattr(settings, 'PARENTAL_CONSENT_AGE_LIMIT', None)
            if age_limit is None:
                return False

        # Return True if either:
        # a) The user has a year of birth specified and that year is fewer years in the past than the limit.
        # b) The user has no year of birth specified and the default is to require consent.
        #
        # Note: we have to be conservative using the user's year of birth as their birth date could be
        # December 31st. This means that if the number of years since their birth year is exactly equal
        # to the age limit then we have to assume that they might still not be old enough.
        year_of_birth = self.year_of_birth
        if year_of_birth is None:
            return default_requires_consent

        if year is None:
            age = self.age
        else:
            age = self._calculate_age(year, year_of_birth)

        return age < age_limit

    def __enumerable_to_display(self, enumerables, enum_value):
        """ Get the human readable value from an enumerable list of key-value pairs. """
        return dict(enumerables)[enum_value]

    def _calculate_age(self, year, year_of_birth):
        """Calculate the youngest age for a user with a given year of birth.

        :param year: year
        :param year_of_birth: year of birth
        :return: youngest age a user could be for the given year
        """
        # There are legal implications regarding how we can contact users and what information we can make public
        # based on their age, so we must take the most conservative estimate.
        return year - year_of_birth - 1

    @classmethod
    def country_cache_key_name(cls, user_id):
        """Return cache key name to be used to cache current country.
        Args:
            user_id(int): Id of user.

        Returns:
            Unicode cache key
        """
        return cls.PROFILE_COUNTRY_CACHE_KEY.format(user_id=user_id)


@receiver(models.signals.post_save, sender=UserProfile)
def invalidate_user_profile_country_cache(sender, instance, **kwargs):  # pylint:   disable=unused-argument
    """Invalidate the cache of country in UserProfile model. """

    changed_fields = getattr(instance, '_changed_fields', {})

    if 'country' in changed_fields:
        cache_key = UserProfile.country_cache_key_name(instance.user_id)
        cache.delete(cache_key)
        log.info("Country changed in UserProfile for %s, cache deleted", instance.user_id)


@receiver(pre_save, sender=UserProfile)
def user_profile_pre_save_callback(sender, **kwargs):
    """
    Ensure consistency of a user profile before saving it.
    """
    user_profile = kwargs['instance']

    # Remove profile images for users who require parental consent
    if user_profile.requires_parental_consent() and user_profile.has_profile_image:
        user_profile.profile_image_uploaded_at = None

    # Cache "old" field values on the model instance so that they can be
    # retrieved in the post_save callback when we emit an event with new and
    # old field values.
    user_profile._changed_fields = get_changed_fields_dict(user_profile, sender)  # lint-amnesty, pylint: disable=protected-access


@receiver(post_save, sender=UserProfile)
def user_profile_post_save_callback(sender, **kwargs):
    """
    Emit analytics events after saving the UserProfile.
    """
    user_profile = kwargs['instance']
    emit_field_changed_events(
        user_profile,
        user_profile.user,
        sender._meta.db_table,
        excluded_fields=['meta']
    )


@receiver(pre_save, sender=User)
def user_pre_save_callback(sender, **kwargs):
    """
    Capture old fields on the user instance before save and cache them as a
    private field on the current model for use in the post_save callback.
    """
    user = kwargs['instance']
    user._changed_fields = get_changed_fields_dict(user, sender)  # lint-amnesty, pylint: disable=protected-access


@receiver(post_save, sender=User)
def user_post_save_callback(sender, **kwargs):
    """
    When a user is modified and either its `is_active` state or email address
    is changed, and the user is, in fact, active, then check to see if there
    are any courses that it needs to be automatically enrolled in and enroll them if needed.

    Additionally, emit analytics events after saving the User.
    """
    user = kwargs['instance']

    changed_fields = user._changed_fields  # lint-amnesty, pylint: disable=protected-access

    if 'is_active' in changed_fields or 'email' in changed_fields:
        if user.is_active:
            ceas = CourseEnrollmentAllowed.for_user(user).filter(auto_enroll=True)

            for cea in ceas:
                # skip enrolling already enrolled users
                if CourseEnrollment.is_enrolled(user, cea.course_id):
                    # Link the CEA to the user if the CEA isn't already linked to the user
                    # (e.g. the user was invited to a course but hadn't activated the account yet)
                    # This is to prevent students from changing e-mails and
                    # enrolling many accounts through the same e-mail.
                    if not cea.user:
                        cea.user = user
                        cea.save()
                    continue

                enrollment = CourseEnrollment.enroll(user, cea.course_id)

                manual_enrollment_audit = ManualEnrollmentAudit.get_manual_enrollment_by_email(user.email)
                if manual_enrollment_audit is not None:
                    # get the enrolled by user and reason from the ManualEnrollmentAudit table.
                    # then create a new ManualEnrollmentAudit table entry for the same email
                    # different transition state.
                    ManualEnrollmentAudit.create_manual_enrollment_audit(
                        manual_enrollment_audit.enrolled_by,
                        user.email,
                        ALLOWEDTOENROLL_TO_ENROLLED,
                        manual_enrollment_audit.reason,
                        enrollment
                    )

    # Ensure the user has a profile when run via management command
    _called_by_management_command = getattr(user, '_called_by_management_command', None)
    if _called_by_management_command:
        try:
            __ = user.profile
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=user)
            log.info('Created new profile for user: %s', user)

    # Because `emit_field_changed_events` removes the record of the fields that
    # were changed, wait to do that until after we've checked them as part of
    # the condition on whether we want to check for automatic enrollments.
    emit_field_changed_events(
        user,
        user,
        sender._meta.db_table,
        excluded_fields=['last_login', 'first_name', 'last_name'],
        hidden_fields=['password']
    )


class UserSignupSource(models.Model):
    """
    This table contains information about users registering
    via Micro-Sites

    .. no_pii:
    """
    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    site = models.CharField(max_length=255, db_index=True)


def unique_id_for_user(user, save='DEPRECATED'):
    """
    Return a unique id for a user, suitable for inserting into
    e.g. personalized survey links.

    Keyword arguments:
    save -- Deprecated and ignored: ID is always saved in an AnonymousUserId object
    """
    if save != 'DEPRECATED':
        warnings.warn(
            "unique_id_for_user no longer accepts save param and now "
            "always saves the ID in the database",
            DeprecationWarning
        )
    # Setting course_id to '' makes it not affect the generated hash,
    # and thus produce the old per-student anonymous id
    return anonymous_id_for_user(user, None)


# TODO: Should be renamed to generic UserGroup, and possibly
# Given an optional field for type of group
class UserTestGroup(models.Model):
    """
    .. no_pii:
    """
    users = models.ManyToManyField(User, db_index=True)
    name = models.CharField(blank=False, max_length=32, db_index=True)
    description = models.TextField(blank=True)


class Registration(models.Model):
    """
    Allows us to wait for e-mail before user is registered. A
    registration profile is created when the user creates an
    account, but that account is inactive. Once the user clicks
    on the activation key, it becomes active.

    .. no_pii:
    """

    class Meta:
        db_table = "auth_registration"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    activation_key = models.CharField(('activation key'), max_length=32, unique=True, db_index=True)
    activation_timestamp = models.DateTimeField(default=None, null=True, blank=True)

    def register(self, user):
        # MINOR TODO: Switch to crypto-secure key
        self.activation_key = uuid.uuid4().hex
        self.user = user
        self.save()

    def activate(self):  # lint-amnesty, pylint: disable=missing-function-docstring
        self.user.is_active = True
        self.user.save(update_fields=['is_active'])
        self.activation_timestamp = datetime.utcnow()
        self.save()
        USER_ACCOUNT_ACTIVATED.send_robust(self.__class__, user=self.user)
        log.info('User %s (%s) account is successfully activated.', self.user.username, self.user.email)


class PendingNameChange(DeletableByUserValue, models.Model):
    """
    This model keeps track of pending requested changes to a user's name.

    .. pii: Contains new_name, retired in LMSAccountRetirementView
    .. pii_types: name
    .. pii_retirement: local_api
    """
    user = models.OneToOneField(User, unique=True, db_index=True, on_delete=models.CASCADE)
    new_name = models.CharField(blank=True, max_length=255)
    rationale = models.CharField(blank=True, max_length=1024)


class PendingEmailChange(DeletableByUserValue, models.Model):
    """
    This model keeps track of pending requested changes to a user's email address.

    .. pii: Contains new_email, retired in AccountRetirementView
    .. pii_types: email_address
    .. pii_retirement: local_api
    """
    user = models.OneToOneField(User, unique=True, db_index=True, on_delete=models.CASCADE)
    new_email = models.CharField(blank=True, max_length=255, db_index=True)
    activation_key = models.CharField(('activation key'), max_length=32, unique=True, db_index=True)

    def request_change(self, email):
        """Request a change to a user's email.

        Implicitly saves the pending email change record.

        Arguments:
            email (unicode): The proposed new email for the user.

        Returns:
            unicode: The activation code to confirm the change.

        """
        self.new_email = email
        self.activation_key = uuid.uuid4().hex
        self.save()
        return self.activation_key


class PendingSecondaryEmailChange(DeletableByUserValue, models.Model):
    """
    This model keeps track of pending requested changes to a user's secondary email address.

    .. pii: Contains new_secondary_email, not currently retired
    .. pii_types: email_address
    .. pii_retirement: retained
    """
    user = models.OneToOneField(User, unique=True, db_index=True, on_delete=models.CASCADE)
    new_secondary_email = models.CharField(blank=True, max_length=255, db_index=True)
    activation_key = models.CharField(('activation key'), max_length=32, unique=True, db_index=True)


EVENT_NAME_ENROLLMENT_ACTIVATED = 'edx.course.enrollment.activated'
EVENT_NAME_ENROLLMENT_DEACTIVATED = 'edx.course.enrollment.deactivated'
EVENT_NAME_ENROLLMENT_MODE_CHANGED = 'edx.course.enrollment.mode_changed'


class LoginFailures(models.Model):
    """
    This model will keep track of failed login attempts.

    .. no_pii:
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    failure_count = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True)

    @classmethod
    def _get_record_for_user(cls, user):
        """
        Gets a user's record, and fixes any duplicates that may have arisen due to get_or_create
        race conditions. See https://code.djangoproject.com/ticket/13906 for details.

        Use this method in place of `LoginFailures.objects.get(user=user)`
        """
        records = LoginFailures.objects.filter(user=user).order_by('-lockout_until')
        for extra_record in records[1:]:
            extra_record.delete()
        return records.get()

    @classmethod
    def is_feature_enabled(cls):
        """
        Returns whether the feature flag around this functionality has been set
        """
        return settings.FEATURES['ENABLE_MAX_FAILED_LOGIN_ATTEMPTS']

    @classmethod
    def is_user_locked_out(cls, user):
        """
        Static method to return in a given user has his/her account locked out
        """
        try:
            record = cls._get_record_for_user(user)
            if not record.lockout_until:
                return False

            now = datetime.now(UTC)
            until = record.lockout_until
            is_locked_out = until and now < until

            return is_locked_out
        except ObjectDoesNotExist:
            return False

    @classmethod
    def increment_lockout_counter(cls, user):
        """
        Ticks the failed attempt counter
        """
        record, _ = LoginFailures.objects.get_or_create(user=user)
        record.failure_count = record.failure_count + 1
        max_failures_allowed = settings.MAX_FAILED_LOGIN_ATTEMPTS_ALLOWED

        # did we go over the limit in attempts
        if record.failure_count >= max_failures_allowed:
            # yes, then store when this account is locked out until
            lockout_period_secs = settings.MAX_FAILED_LOGIN_ATTEMPTS_LOCKOUT_PERIOD_SECS
            record.lockout_until = datetime.now(UTC) + timedelta(seconds=lockout_period_secs)

        record.save()

    @classmethod
    def check_user_reset_password_threshold(cls, user):
        """
        Checks if the user is above threshold for reset password message.
        """
        record, _ = LoginFailures.objects.get_or_create(user=user)
        max_failures_allowed = settings.MAX_FAILED_LOGIN_ATTEMPTS_ALLOWED

        return record.failure_count >= max_failures_allowed / 2, record.failure_count

    @classmethod
    def clear_lockout_counter(cls, user):
        """
        Removes the lockout counters (normally called after a successful login)
        """
        try:
            entry = cls._get_record_for_user(user)
            entry.delete()
        except ObjectDoesNotExist:
            return

    def __str__(self):
        """Str -> Username: count - date."""
        return '{username}: {count} - {date}'.format(
            username=self.user.username,
            count=self.failure_count,
            date=self.lockout_until.isoformat() if self.lockout_until else '-'
        )

    class Meta:
        verbose_name = 'Login Failure'
        verbose_name_plural = 'Login Failures'


class CourseEnrollmentException(Exception):
    pass


class NonExistentCourseError(CourseEnrollmentException):
    pass


class EnrollmentClosedError(CourseEnrollmentException):
    pass


class CourseFullError(CourseEnrollmentException):
    pass


class AlreadyEnrolledError(CourseEnrollmentException):
    pass


class EnrollmentNotAllowed(CourseEnrollmentException):
    pass


class UnenrollmentNotAllowed(CourseEnrollmentException):
    pass


class CourseEnrollmentManager(models.Manager):
    """
    Custom manager for CourseEnrollment with Table-level filter methods.
    """

    def is_small_course(self, course_id):
        """
        Returns false if the number of enrollments are one greater than 'max_enrollments' else true

        'course_id' is the course_id to return enrollments
        """
        max_enrollments = settings.FEATURES.get("MAX_ENROLLMENT_INSTR_BUTTONS")

        enrollment_number = super().get_queryset().filter(
            course_id=course_id,
            is_active=1
        )[:max_enrollments + 1].count()

        return enrollment_number <= max_enrollments

    def num_enrolled_in_exclude_admins(self, course_id):
        """
        Returns the count of active enrollments in a course excluding instructors, staff and CCX coaches.

        Arguments:
            course_id (CourseLocator): course_id to return enrollments (count).

        Returns:
            int: Count of enrollments excluding staff, instructors and CCX coaches.

        """
        # To avoid circular imports.
        from common.djangoapps.student.roles import CourseCcxCoachRole, CourseInstructorRole, CourseStaffRole
        course_locator = course_id

        if getattr(course_id, 'ccx', None):
            course_locator = course_id.to_course_locator()

        staff = CourseStaffRole(course_locator).users_with_role()
        admins = CourseInstructorRole(course_locator).users_with_role()
        coaches = CourseCcxCoachRole(course_locator).users_with_role()

        return super().get_queryset().filter(
            course_id=course_id,
            is_active=1,
        ).exclude(user__in=staff).exclude(user__in=admins).exclude(user__in=coaches).count()

    def is_course_full(self, course):
        """
        Returns a boolean value regarding whether a course has already reached it's max enrollment
        capacity
        """
        is_course_full = False
        if course.max_student_enrollments_allowed is not None:
            is_course_full = self.num_enrolled_in_exclude_admins(course.id) >= course.max_student_enrollments_allowed

        return is_course_full

    def users_enrolled_in(self, course_id, include_inactive=False, verified_only=False):
        """
        Return a queryset of User for every user enrolled in the course.

        Arguments:
            course_id (CourseLocator): course_id to return enrollees for.
            include_inactive (boolean): is a boolean when True, returns both active and inactive enrollees
            verified_only (boolean): is a boolean when True, returns only verified enrollees.

        Returns:
            Returns a User queryset.
        """
        filter_kwargs = {
            'courseenrollment__course_id': course_id,
        }
        if not include_inactive:
            filter_kwargs['courseenrollment__is_active'] = True
        if verified_only:
            filter_kwargs['courseenrollment__mode'] = CourseMode.VERIFIED
        return User.objects.filter(**filter_kwargs)

    def enrollment_counts(self, course_id):
        """
        Returns a dictionary that stores the total enrollment count for a course, as well as the
        enrollment count for each individual mode.
        """
        # Unfortunately, Django's "group by"-style queries look super-awkward
        query = use_read_replica_if_available(
            super().get_queryset().filter(course_id=course_id, is_active=True).values(
                'mode').order_by().annotate(Count('mode')))
        total = 0
        enroll_dict = defaultdict(int)
        for item in query:
            enroll_dict[item['mode']] = item['mode__count']
            total += item['mode__count']
        enroll_dict['total'] = total
        return enroll_dict

    def enrolled_and_dropped_out_users(self, course_id):
        """Return a queryset of Users in the course."""
        return User.objects.filter(
            courseenrollment__course_id=course_id
        )


# Named tuple for fields pertaining to the state of
# CourseEnrollment for a user in a course.  This type
# is used to cache the state in the request cache.
CourseEnrollmentState = namedtuple('CourseEnrollmentState', 'mode, is_active')


class CourseEnrollment(models.Model):
    """
    Represents a Student's Enrollment record for a single Course. You should
    generally not manipulate CourseEnrollment objects directly, but use the
    classmethods provided to enroll, unenroll, or check on the enrollment status
    of a given student.

    We're starting to consolidate course enrollment logic in this class, but
    more should be brought in (such as checking against CourseEnrollmentAllowed,
    checking course dates, user permissions, etc.) This logic is currently
    scattered across our views.

    .. no_pii:
    """
    MODEL_TAGS = ['course', 'is_active', 'mode']

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    course = models.ForeignKey(
        CourseOverview,
        db_constraint=False,
        on_delete=models.DO_NOTHING,
    )

    @property
    def course_price(self):
        return get_cosmetic_verified_display_price(self.course)

    created = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    # If is_active is False, then the student is not considered to be enrolled
    # in the course (is_enrolled() will return False)
    is_active = models.BooleanField(default=True)

    # Represents the modes that are possible. We'll update this later with a
    # list of possible values.
    mode = models.CharField(default=CourseMode.get_default_mode_slug, max_length=100)

    # An audit row will be created for every change to a CourseEnrollment. This
    # will create a new model behind the scenes - HistoricalCourseEnrollment and a
    # table named 'student_courseenrollment_history'.
    history = HistoricalRecords(
        history_id_field=models.UUIDField(default=uuid.uuid4),
        table_name='student_courseenrollment_history'
    )

    objects = CourseEnrollmentManager()

    # cache key format e.g enrollment.<username>.<course_key>.mode = 'honor'
    COURSE_ENROLLMENT_CACHE_KEY = "enrollment.{}.{}.mode"  # TODO Can this be removed?  It doesn't seem to be used.

    MODE_CACHE_NAMESPACE = 'CourseEnrollment.mode_and_active'

    class Meta:
        unique_together = (('user', 'course'), )
        indexes = [Index(fields=['user', '-created'])]
        ordering = ('user', 'course')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Private variable for storing course_overview to minimize calls to the database.
        # When the property .course_overview is accessed for the first time, this variable will be set.
        self._course_overview = None

    def __str__(self):
        return (
            "[CourseEnrollment] {}: {} ({}); active: ({})"
        ).format(self.user, self.course_id, self.created, self.is_active)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields
        )

        # Delete the cached status hash, forcing the value to be recalculated the next time it is needed.
        cache.delete(self.enrollment_status_hash_cache_key(self.user))

    @classmethod
    def get_or_create_enrollment(cls, user, course_key):
        """
        Create an enrollment for a user in a class. By default *this enrollment
        is not active*. This is useful for when an enrollment needs to go
        through some sort of approval process before being activated. If you
        don't need this functionality, just call `enroll()` instead.

        Returns a CourseEnrollment object.

        `user` is a Django User object. If it hasn't been saved yet (no `.id`
               attribute), this method will automatically save it before
               adding an enrollment for it.

        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)

        It is expected that this method is called from a method which has already
        verified the user authentication and access.

        If the enrollment is done due to a CourseEnrollmentAllowed, the CEA will be
        linked to the user being enrolled so that it can't be used by other users.
        """
        # If we're passing in a newly constructed (i.e. not yet persisted) User,
        # save it to the database so that it can have an ID that we can throw
        # into our CourseEnrollment object. Otherwise, we'll get an
        # IntegrityError for having a null user_id.
        assert isinstance(course_key, CourseKey)

        if user.id is None:
            user.save()

        enrollment, __ = cls.objects.get_or_create(
            user=user,
            course_id=course_key,
            defaults={
                'mode': CourseMode.DEFAULT_MODE_SLUG,
                'is_active': False
            }
        )

        # If there was an unlinked CEA, it becomes linked now
        CourseEnrollmentAllowed.objects.filter(
            email=user.email,
            course_id=course_key,
            user__isnull=True
        ).update(user=user)

        return enrollment

    @classmethod
    def get_enrollment(cls, user, course_key, select_related=None):
        """Returns a CourseEnrollment object.

        Args:
            user (User): The user associated with the enrollment.
            course_key (CourseKey): The key of the course associated with the enrollment.

        Returns:
            Course enrollment object or None
        """
        assert user

        if user.is_anonymous:
            return None
        try:
            request_cache = RequestCache('get_enrollment')
            if select_related:
                cache_key = (user.id, course_key, ','.join(select_related))
            else:
                cache_key = (user.id, course_key)
            cache_response = request_cache.get_cached_response(cache_key)
            if cache_response.is_found:
                return cache_response.value

            query = cls.objects
            if select_related is not None:
                query = query.select_related(*select_related)
            enrollment = query.get(
                user=user,
                course_id=course_key
            )
            request_cache.set(cache_key, enrollment)
            return enrollment
        except cls.DoesNotExist:
            return None

    @classmethod
    def is_enrollment_closed(cls, user, course):
        """
        Returns a boolean value regarding whether the user has access to enroll in the course. Returns False if the
        enrollment has been closed.
        """
        from openedx.core.djangoapps.enrollments.permissions import ENROLL_IN_COURSE
        return not user.has_perm(ENROLL_IN_COURSE, course)

    def update_enrollment(self, mode=None, is_active=None, skip_refund=False, enterprise_uuid=None):
        """
        Updates an enrollment for a user in a class.  This includes options
        like changing the mode, toggling is_active True/False, etc.

        Also emits relevant events for analytics purposes.

        This saves immediately.

        """
        RequestCache('get_enrollment').clear()

        activation_changed = False
        # if is_active is None, then the call to update_enrollment didn't specify
        # any value, so just leave is_active as it is
        if self.is_active != is_active and is_active is not None:
            self.is_active = is_active
            activation_changed = True

        mode_changed = False
        # if mode is None, the call to update_enrollment didn't specify a new
        # mode, so leave as-is
        if self.mode != mode and mode is not None:
            self.mode = mode
            mode_changed = True

        try:
            course_data = CourseData(
                course_key=self.course_id,
                display_name=self.course.display_name,
            )
        except CourseOverview.DoesNotExist:
            course_data = CourseData(
                course_key=self.course_id,
            )

        if activation_changed or mode_changed:
            self.save()
            self._update_enrollment_in_request_cache(
                self.user,
                self.course_id,
                CourseEnrollmentState(self.mode, self.is_active),
            )

            # .. event_implemented_name: COURSE_ENROLLMENT_CHANGED
            COURSE_ENROLLMENT_CHANGED.send_event(
                enrollment=CourseEnrollmentData(
                    user=UserData(
                        pii=UserPersonalData(
                            username=self.user.username,
                            email=self.user.email,
                            name=self.user.profile.name,
                        ),
                        id=self.user.id,
                        is_active=self.user.is_active,
                    ),
                    course=course_data,
                    mode=self.mode,
                    is_active=self.is_active,
                    creation_date=self.created,
                )
            )

        if activation_changed:
            if self.is_active:
                self.emit_event(EVENT_NAME_ENROLLMENT_ACTIVATED, enterprise_uuid=enterprise_uuid)
            else:
                UNENROLL_DONE.send(sender=None, course_enrollment=self, skip_refund=skip_refund)
                self.emit_event(EVENT_NAME_ENROLLMENT_DEACTIVATED)
                self.send_signal(EnrollStatusChange.unenroll)

                # .. event_implemented_name: COURSE_UNENROLLMENT_COMPLETED
                COURSE_UNENROLLMENT_COMPLETED.send_event(
                    enrollment=CourseEnrollmentData(
                        user=UserData(
                            pii=UserPersonalData(
                                username=self.user.username,
                                email=self.user.email,
                                name=self.user.profile.name,
                            ),
                            id=self.user.id,
                            is_active=self.user.is_active,
                        ),
                        course=course_data,
                        mode=self.mode,
                        is_active=self.is_active,
                        creation_date=self.created,
                    )
                )

        if mode_changed:
            # If mode changed to one that requires proctoring, send proctoring requirements email
            if should_send_proctoring_requirements_email(self.user.username, self.course_id):
                email_context = generate_proctoring_requirements_email_context(self.user, self.course_id)
                send_proctoring_requirements_email(context=email_context)

            # Only emit mode change events when the user's enrollment
            # mode has changed from its previous setting
            self.emit_event(EVENT_NAME_ENROLLMENT_MODE_CHANGED)
            # this signal is meant to trigger a score recalculation celery task,
            # `countdown` is added to celery task as delay so that cohort is duly updated
            # before starting score recalculation
            ENROLLMENT_TRACK_UPDATED.send(
                sender=None,
                user=self.user,
                course_key=self.course_id,
                mode=self.mode,
                countdown=SCORE_RECALCULATION_DELAY_ON_ENROLLMENT_UPDATE,
            )

    def send_signal(self, event, cost=None, currency=None):
        """
        Sends a signal announcing changes in course enrollment status.
        """
        ENROLL_STATUS_CHANGE.send(sender=None, event=event, user=self.user,
                                  mode=self.mode, course_id=self.course_id,
                                  cost=cost, currency=currency)

    @classmethod
    def send_signal_full(cls, event, user=user, mode=mode, course_id=None, cost=None, currency=None):
        """
        Sends a signal announcing changes in course enrollment status.
        This version should be used if you don't already have a CourseEnrollment object
        """
        ENROLL_STATUS_CHANGE.send(sender=None, event=event, user=user,
                                  mode=mode, course_id=course_id,
                                  cost=cost, currency=currency)

    def emit_event(self, event_name, enterprise_uuid=None):
        """
        Emits an event to explicitly track course enrollment and unenrollment.
        """
        from openedx.core.djangoapps.schedules.config import set_up_external_updates_for_enrollment

        try:
            context = contexts.course_context_from_course_id(self.course_id)
            if enterprise_uuid:
                context["enterprise_uuid"] = enterprise_uuid
            assert isinstance(self.course_id, CourseKey)
            data = {
                'user_id': self.user.id,
                'course_id': str(self.course_id),
                'mode': self.mode,
            }
            if enterprise_uuid and 'username' not in context:
                data['username'] = self.user.username

            segment_properties = {
                'category': 'conversion',
                'label': str(self.course_id),
                'org': self.course_id.org,
                'course': self.course_id.course,
                'run': self.course_id.run,
                'mode': self.mode,
            }
            # DENG-803: For segment events forwarded along to Hubspot, duplicate the `properties`
            # section of the event payload into the `traits` section so that they can be received.
            # This is a temporary fix until we implement this behavior outside of the LMS.
            # TODO: DENG-804: remove the properties duplication in the event traits.
            segment_traits = dict(segment_properties)
            # Add course_title to the traits, as it is used by Hubspot filters
            segment_traits['course_title'] = self.course_overview.display_name if self.course_overview else None
            # Hubspot requires all incoming events have an email address to link it
            # to a Contact object.
            segment_traits['email'] = self.user.email

            if event_name == EVENT_NAME_ENROLLMENT_ACTIVATED:
                segment_properties['email'] = self.user.email
                # This next property is for an experiment, see method's comments for more information
                segment_properties['external_course_updates'] = set_up_external_updates_for_enrollment(self.user,
                                                                                                       self.course_id)
                segment_properties['course_start'] = self.course.start
                segment_properties['course_pacing'] = self.course.pacing
            with tracker.get_tracker().context(event_name, context):
                tracker.emit(event_name, data)
                segment.track(self.user_id, event_name, segment_properties, traits=segment_traits)

        except Exception:  # pylint: disable=broad-except
            if event_name and self.course_id:
                log.exception(
                    'Unable to emit event %s for user %s and course %s',
                    event_name,
                    self.user.username,
                    self.course_id,
                )

    @classmethod
    def enroll(cls, user, course_key, mode=None, check_access=False, can_upgrade=False, enterprise_uuid=None):
        """
        Enroll a user in a course. This saves immediately.

        Returns a CourseEnrollment object.

        `user` is a Django User object. If it hasn't been saved yet (no `.id`
               attribute), this method will automatically save it before
               adding an enrollment for it.

        `course_key` is our usual course_id string (e.g. "edX/Test101/2013_Fall)

        `mode` is a string specifying what kind of enrollment this is. The
               default is the default course mode, 'audit'. Other options
               include 'professional', 'verified', 'honor',
               'no-id-professional' and 'credit'.
               See CourseMode in common/djangoapps/course_modes/models.py.

        `check_access`: if True, we check that an accessible course actually
                exists for the given course_key before we enroll the student.
                The default is set to False to avoid breaking legacy code or
                code with non-standard flows (ex. beta tester invitations), but
                for any standard enrollment flow you probably want this to be True.

        `can_upgrade`: if course is upgradeable, alow learners to enroll even
                if enrollment is closed. This is a special case for entitlements
                while selecting a session. The default is set to False to avoid
                breaking the orignal course enroll code.

        enterprise_uuid (str): Add course enterprise uuid

        Exceptions that can be raised: NonExistentCourseError,
        EnrollmentClosedError, CourseFullError, AlreadyEnrolledError.  All these
        are subclasses of CourseEnrollmentException if you want to catch all of
        them in the same way.

        It is expected that this method is called from a method which has already
        verified the user authentication.

        Also emits relevant events for analytics purposes.
        """
        try:
            user, course_key, mode = CourseEnrollmentStarted.run_filter(
                user=user, course_key=course_key, mode=mode,
            )
        except CourseEnrollmentStarted.PreventEnrollment as exc:
            raise EnrollmentNotAllowed(str(exc)) from exc

        if mode is None:
            mode = _default_course_mode(str(course_key))
        # All the server-side checks for whether a user is allowed to enroll.
        try:
            course = CourseOverview.get_from_id(course_key)
            course_data = CourseData(
                course_key=course.id,
                display_name=course.display_name,
            )
        except CourseOverview.DoesNotExist:
            # This is here to preserve legacy behavior which allowed enrollment in courses
            # announced before the start of content creation.
            course_data = CourseData(
                course_key=course_key,
            )
            if check_access:
                log.warning("User %s failed to enroll in non-existent course %s", user.username, str(course_key))
                raise NonExistentCourseError  # lint-amnesty, pylint: disable=raise-missing-from

        if check_access:
            if cls.is_enrollment_closed(user, course) and not can_upgrade:
                log.warning(
                    "User %s failed to enroll in course %s because enrollment is closed",
                    user.username,
                    str(course_key)
                )
                raise EnrollmentClosedError

            if cls.objects.is_course_full(course):
                log.warning(
                    "Course %s has reached its maximum enrollment of %d learners. User %s failed to enroll.",
                    str(course_key),
                    course.max_student_enrollments_allowed,
                    user.username,
                )
                raise CourseFullError
        if cls.is_enrolled(user, course_key):
            log.warning(
                "User %s attempted to enroll in %s, but they were already enrolled",
                user.username,
                str(course_key)
            )
            if check_access:
                raise AlreadyEnrolledError

        # User is allowed to enroll if they've reached this point.
        enrollment = cls.get_or_create_enrollment(user, course_key)
        enrollment.update_enrollment(is_active=True, mode=mode, enterprise_uuid=enterprise_uuid)
        enrollment.send_signal(EnrollStatusChange.enroll)

        # .. event_implemented_name: COURSE_ENROLLMENT_CREATED
        COURSE_ENROLLMENT_CREATED.send_event(
            enrollment=CourseEnrollmentData(
                user=UserData(
                    pii=UserPersonalData(
                        username=user.username,
                        email=user.email,
                        name=user.profile.name,
                    ),
                    id=user.id,
                    is_active=user.is_active,
                ),
                course=course_data,
                mode=enrollment.mode,
                is_active=enrollment.is_active,
                creation_date=enrollment.created,
            )
        )

        return enrollment

    @classmethod
    def enroll_by_email(cls, email, course_id, mode=None, ignore_errors=True):
        """
        Enroll a user in a course given their email. This saves immediately.

        Note that  enrolling by email is generally done in big batches and the
        error rate is high. For that reason, we supress User lookup errors by
        default.

        Returns a CourseEnrollment object. If the User does not exist and
        `ignore_errors` is set to `True`, it will return None.

        `email` Email address of the User to add to enroll in the course.

        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)

        `mode` is a string specifying what kind of enrollment this is. The
               default is the default course mode, 'audit'. Other options
               include 'professional', 'verified', 'honor',
               'no-id-professional' and 'credit'.
               See CourseMode in common/djangoapps/course_modes/models.py.

        `ignore_errors` is a boolean indicating whether we should suppress
                        `User.DoesNotExist` errors (returning None) or let it
                        bubble up.

        It is expected that this method is called from a method which has already
        verified the user authentication and access.
        """
        try:
            user = User.objects.get(email=email)
            return cls.enroll(user, course_id, mode)
        except User.DoesNotExist:
            err_msg = "Tried to enroll email {} into course {}, but user not found"
            log.error(err_msg.format(email, course_id))
            if ignore_errors:
                return None
            raise

    @classmethod
    def unenroll(cls, user, course_id, skip_refund=False):
        """
        Remove the user from a given course. If the relevant `CourseEnrollment`
        object doesn't exist, we log an error but don't throw an exception.

        `user` is a Django User object. If it hasn't been saved yet (no `.id`
               attribute), this method will automatically save it before
               adding an enrollment for it.

        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)

        `skip_refund` can be set to True to avoid the refund process.
        """
        RequestCache('get_enrollment').clear()

        try:
            record = cls.objects.get(user=user, course_id=course_id)

            try:
                # .. filter_implemented_name: CourseUnenrollmentStarted
                # .. filter_type: org.openedx.learning.course.unenrollment.started.v1
                record = CourseUnenrollmentStarted.run_filter(enrollment=record)
            except CourseUnenrollmentStarted.PreventUnenrollment as exc:
                raise UnenrollmentNotAllowed(str(exc)) from exc

            record.update_enrollment(is_active=False, skip_refund=skip_refund)

        except cls.DoesNotExist:
            log.error(
                "Tried to unenroll student %s from %s but they were not enrolled",
                user,
                course_id
            )

    @classmethod
    def unenroll_by_email(cls, email, course_id):
        """
        Unenroll a user from a course given their email. This saves immediately.
        User lookup errors are logged but will not throw an exception.

        `email` Email address of the User to unenroll from the course.

        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)
        """
        RequestCache('get_enrollment').clear()

        try:
            user = User.objects.get(email=email)
            return cls.unenroll(user, course_id)
        except User.DoesNotExist:
            log.error(
                "Tried to unenroll email %s from course %s, but user not found",
                email,
                course_id
            )

    @classmethod
    def is_enrolled(cls, user, course_key):
        """
        Returns True if the user is enrolled in the course (the entry must exist
        and it must have `is_active=True`). Otherwise, returns False.

        `user` is a Django User object. If it hasn't been saved yet (no `.id`
               attribute), this method will automatically save it before
               adding an enrollment for it.

        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)
        """
        enrollment_state = cls._get_enrollment_state(user, course_key)
        return enrollment_state.is_active or False

    @classmethod
    def is_enrolled_by_partial(cls, user, course_id_partial):
        """
        Returns `True` if the user is enrolled in a course that starts with
        `course_id_partial`. Otherwise, returns False.

        Can be used to determine whether a student is enrolled in a course
        whose run name is unknown.

        `user` is a Django User object. If it hasn't been saved yet (no `.id`
               attribute), this method will automatically save it before
               adding an enrollment for it.

        `course_id_partial` (CourseKey) is missing the run component
        """
        assert isinstance(course_id_partial, CourseKey)
        assert not course_id_partial.run  # None or empty string
        course_key = CourseKey.from_string('/'.join([course_id_partial.org, course_id_partial.course, '']))
        querystring = str(course_key)
        try:
            return cls.objects.filter(
                user=user,
                course__id__startswith=querystring,
                is_active=1
            ).exists()
        except cls.DoesNotExist:
            return False

    @classmethod
    def enrollment_mode_for_user(cls, user, course_id):
        """
        Returns the enrollment mode for the given user for the given course

        `user` is a Django User object
        `course_id` is our usual course_id string (e.g. "edX/Test101/2013_Fall)

        Returns (mode, is_active) where mode is the enrollment mode of the student
            and is_active is whether the enrollment is active.
        Returns (None, None) if the courseenrollment record does not exist.
        """
        enrollment_state = cls._get_enrollment_state(user, course_id)
        return enrollment_state.mode, enrollment_state.is_active

    @classmethod
    def enrollments_for_user(cls, user):
        return cls.objects.filter(user=user, is_active=1).select_related('user')

    @classmethod
    def enrollments_for_user_with_overviews_preload(cls, user, courses_limit=None):  # pylint: disable=invalid-name
        """
        List of user's CourseEnrollments, CourseOverviews preloaded if possible.

        We try to preload all CourseOverviews, which are usually lazily loaded
        as the .course_overview property. This is to avoid making an extra
        query for every enrollment when displaying something like the student
        dashboard. If some of the CourseOverviews are not found, we make no
        attempt to initialize them -- we just fall back to existing lazy-load
        behavior. The goal is to optimize the most common case as simply as
        possible, without changing any of the existing contracts.

        The name of this method is long, but was the end result of hashing out a
        number of alternatives, so pylint can stuff it (disable=invalid-name)
        """
        enrollments = cls.enrollments_for_user(user).select_related('schedule', 'course', 'course__image_set')

        if courses_limit:
            return enrollments.order_by('-created')[:courses_limit]
        else:
            return enrollments

    @classmethod
    def enrollment_status_hash_cache_key(cls, user):
        """ Returns the cache key for the cached enrollment status hash.

        Args:
            user (User): User whose cache key should be returned.

        Returns:
            str: Cache key.
        """
        return 'enrollment_status_hash_' + user.username

    @classmethod
    def generate_enrollment_status_hash(cls, user):
        """ Generates a hash encoding the given user's *active* enrollments.

         Args:
             user (User): User whose enrollments should be hashed.

        Returns:
            str: Hash of the user's active enrollments. If the user is anonymous, `None` is returned.
        """
        assert user

        if user.is_anonymous:
            return None

        cache_key = cls.enrollment_status_hash_cache_key(user)
        status_hash = cache.get(cache_key)

        if not status_hash:
            enrollments = cls.enrollments_for_user(user).values_list('course_id', 'mode')
            enrollments = [(str(e[0]).lower(), e[1].lower()) for e in enrollments]
            enrollments = sorted(enrollments, key=lambda e: e[0])
            hash_elements = [user.username]
            hash_elements += [f'{e[0]}={e[1]}' for e in enrollments]
            status_hash = hashlib.md5('&'.join(hash_elements).encode('utf-8')).hexdigest()

            # The hash is cached indefinitely. It will be invalidated when the user enrolls/unenrolls.
            cache.set(cache_key, status_hash, None)

        return status_hash

    def is_paid_course(self):
        """
        Returns True, if course is paid
        """
        paid_course = CourseMode.is_white_label(self.course_id)
        if paid_course or CourseMode.is_professional_slug(self.mode):
            return True

        return False

    def activate(self):
        """Makes this `CourseEnrollment` record active. Saves immediately."""
        self.update_enrollment(is_active=True)

    def deactivate(self):
        """Makes this `CourseEnrollment` record inactive. Saves immediately. An
        inactive record means that the student is not enrolled in this course.
        """
        self.update_enrollment(is_active=False)

    def change_mode(self, mode):
        """Changes this `CourseEnrollment` record's mode to `mode`.  Saves immediately."""
        self.update_enrollment(mode=mode)

    def refundable(self):
        """
        For paid/verified certificates, students may always receive a refund if
        this CourseEnrollment's `can_refund` attribute is not `None` (that
        overrides all other rules).

        If the `.can_refund` attribute is `None` or doesn't exist, then ALL of
        the following must be true for this enrollment to be refundable:

            * The user does not have a certificate issued for this course.
            * We are not past the refund cutoff date
            * There exists a 'verified' CourseMode for this course.

        Returns:
            bool: Whether is CourseEnrollment can be refunded.
        """
        # In order to support manual refunds past the deadline, set can_refund on this object.
        # On unenrolling, the "UNENROLL_DONE" signal calls CertificateItem.refund_cert_callback(),
        # which calls this method to determine whether to refund the order.
        # This can't be set directly because refunds currently happen as a side-effect of unenrolling.
        # (side-effects are bad)

        if getattr(self, 'can_refund', None) is not None:
            return True

        # Due to circular import issues this import was placed close to usage. To move this to the
        # top of the file would require a large scale refactor of the refund code.
        import lms.djangoapps.certificates.api
        # If the student has already been given a certificate in a non refundable status they should not be refunded
        certificate = lms.djangoapps.certificates.api.get_certificate_for_user_id(
            self.user,
            self.course_id
        )
        if certificate and not CertificateStatuses.is_refundable_status(certificate.status):
            return False

        # If it is after the refundable cutoff date they should not be refunded.
        refund_cutoff_date = self.refund_cutoff_date()
        # `refund_cuttoff_date` will be `None` if there is no order. If there is no order return `False`.
        if refund_cutoff_date is None:
            return False
        if datetime.now(UTC) > refund_cutoff_date:
            return False

        course_mode = CourseMode.mode_for_course(self.course_id, 'verified', include_expired=True)
        if course_mode is None:
            return False
        else:
            return True

    def refund_cutoff_date(self):
        """ Calculate and return the refund window end date. """
        # NOTE: This is here to avoid circular references
        from openedx.core.djangoapps.commerce.utils import ECOMMERCE_DATE_FORMAT
        date_placed = self.get_order_attribute_value('date_placed')

        if not date_placed:
            order_number = self.get_order_attribute_value('order_number')
            if not order_number:
                return None

            date_placed = self.get_order_attribute_from_ecommerce('date_placed')
            if not date_placed:
                return None

            # also save the attribute so that we don't need to call ecommerce again.
            username = self.user.username
            enrollment_attributes = get_enrollment_attributes(username, str(self.course_id))
            enrollment_attributes.append(
                {
                    "namespace": "order",
                    "name": "date_placed",
                    "value": date_placed,
                }
            )
            set_enrollment_attributes(username, str(self.course_id), enrollment_attributes)

        refund_window_start_date = max(
            datetime.strptime(date_placed, ECOMMERCE_DATE_FORMAT),
            self.course_overview.start.replace(tzinfo=None)
        )

        return refund_window_start_date.replace(tzinfo=UTC) + EnrollmentRefundConfiguration.current().refund_window

    def is_order_voucher_refundable(self):
        """ Checks if the coupon batch expiration date has passed to determine whether order voucher is refundable. """
        from openedx.core.djangoapps.commerce.utils import ECOMMERCE_DATE_FORMAT
        vouchers = self.get_order_attribute_from_ecommerce('vouchers')
        if not vouchers:
            return False
        voucher_end_datetime_str = vouchers[0]['end_datetime']
        voucher_expiration_date = datetime.strptime(voucher_end_datetime_str, ECOMMERCE_DATE_FORMAT).replace(tzinfo=UTC)
        return datetime.now(UTC) < voucher_expiration_date

    def get_order_attribute_from_ecommerce(self, attribute_name):
        """
        Fetches the order details from ecommerce to return the value of the attribute passed as argument.

        Arguments:
            attribute_name (str): The name of the attribute that you want to fetch from response e:g 'number' or
            'vouchers', etc.

        Returns:
            (str | array | None): Returns the attribute value if it exists, returns None if the order doesn't exist or
            attribute doesn't exist in the response.
        """

        # NOTE: This is here to avoid circular references
        from openedx.core.djangoapps.commerce.utils import ecommerce_api_client
        order_number = self.get_order_attribute_value('order_number')
        if not order_number:
            return None

        # check if response is already cached
        cache_key = get_cache_key(user_id=self.user.id, order_number=order_number)
        cached_response = TieredCache.get_cached_response(cache_key)
        if cached_response.is_found:
            order = cached_response.value
        else:
            try:
                # response is not cached, so make a call to ecommerce to fetch order details
                order = ecommerce_api_client(self.user).orders(order_number).get()
            except HttpClientError:
                log.warning(
                    "Encountered HttpClientError while getting order details from ecommerce. "
                    "Order={number} and user {user}".format(number=order_number, user=self.user.id))
                return None

            except HttpServerError:
                log.warning(
                    "Encountered HttpServerError while getting order details from ecommerce. "
                    "Order={number} and user {user}".format(number=order_number, user=self.user.id))
                return None

            except SlumberBaseException:
                log.warning(
                    "Encountered an error while getting order details from ecommerce. "
                    "Order={number} and user {user}".format(number=order_number, user=self.user.id))
                return None

            cache_time_out = getattr(settings, 'ECOMMERCE_ORDERS_API_CACHE_TIMEOUT', 3600)
            TieredCache.set_all_tiers(cache_key, order, cache_time_out)
        try:
            return order[attribute_name]
        except KeyError:
            return None

    def get_order_attribute_value(self, attr_name):
        """ Get and return course enrollment order attribute's value."""
        try:
            attribute = self.attributes.get(namespace='order', name=attr_name)
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            # If there are multiple attributes then return the last one.
            enrollment_id = self.get_enrollment(self.user, self.course_id).id
            log.warning(
                "Multiple CourseEnrollmentAttributes found for user %s with enrollment-ID %s",
                self.user.id,
                enrollment_id
            )
            attribute = self.attributes.filter(namespace='order', name=attr_name).last()

        return attribute.value

    @property
    def username(self):
        return self.user.username

    @property
    def course_overview(self):
        """
        Returns a CourseOverview of the course to which this enrollment refers.
        Returns None if an error occurred while trying to load the course.

        Note:
            If the course is re-published within the lifetime of this
            CourseEnrollment object, then the value of this property will
            become stale.
        """
        if not self._course_overview:
            try:
                self._course_overview = self.course
            except CourseOverview.DoesNotExist:
                log.info('Course Overviews: unable to find course overview for enrollment, loading from modulestore.')
                try:
                    self._course_overview = CourseOverview.get_from_id(self.course_id)
                except (CourseOverview.DoesNotExist, OSError):
                    self._course_overview = None
        return self._course_overview

    @cached_property
    def verified_mode(self):
        return CourseMode.verified_mode_for_course(self.course_id)

    @cached_property
    def upgrade_deadline(self):
        """
        Returns the upgrade deadline for this enrollment, if it is upgradeable.
        If the seat cannot be upgraded, None is returned.
        Note:
            When loading this model, use `select_related` to retrieve the associated schedule object.
        Returns:
            datetime|None
        """
        log.debug('Schedules: Determining upgrade deadline for CourseEnrollment %d...', self.id)
        if not CourseMode.is_mode_upgradeable(self.mode):
            log.debug(
                'Schedules: %s mode of %s is not upgradeable. Returning None for upgrade deadline.',
                self.mode, self.course_id
            )
            return None

        if self.dynamic_upgrade_deadline is not None:
            # When course modes expire they aren't found any more and None would be returned.
            # Replicate that behavior here by returning None if the personalized deadline is in the past.
            if self.dynamic_upgrade_deadline <= datetime.now(UTC):
                log.debug('Schedules: Returning None since dynamic upgrade deadline has already passed.')
                return None

            if self.verified_mode is None or CourseMode.is_professional_mode(self.verified_mode):
                log.debug('Schedules: Returning None for dynamic upgrade deadline since the course does not have a '
                          'verified mode.')
                return None

            return self.dynamic_upgrade_deadline

        return self.course_upgrade_deadline

    @cached_property
    def dynamic_upgrade_deadline(self):
        """
        Returns the learner's personalized upgrade deadline if one exists, otherwise it returns None.

        Note that this will return a value even if the deadline is in the past. This property can be used
        to modify behavior for users with personalized deadlines by checking if it's None or not.

        Returns:
            datetime|None
        """
        if not self.course_overview.self_paced:
            return None

        if not DynamicUpgradeDeadlineConfiguration.is_enabled():
            return None

        course_config = CourseDynamicUpgradeDeadlineConfiguration.current(self.course_id)
        if course_config.opted_out():
            # Course-level config should be checked first since it overrides the org-level config
            return None

        org_config = OrgDynamicUpgradeDeadlineConfiguration.current(self.course_id.org)
        if org_config.opted_out() and not course_config.opted_in():
            return None

        try:
            if not self.schedule or not self.schedule.enrollment.is_active:  # pylint: disable=no-member
                return None

            log.debug(
                'Schedules: Pulling upgrade deadline for CourseEnrollment %d from Schedule %d.',
                self.id, self.schedule.id  # lint-amnesty, pylint: disable=no-member
            )
            return self.schedule.upgrade_deadline  # lint-amnesty, pylint: disable=no-member
        except ObjectDoesNotExist:
            # NOTE: Schedule has a one-to-one mapping with CourseEnrollment. If no schedule is associated
            # with this enrollment, Django will raise an exception rather than return None.
            log.debug('Schedules: No schedule exists for CourseEnrollment %d.', self.id)
            return None

    @cached_property
    def course_upgrade_deadline(self):
        """
        Returns the expiration datetime for the verified course mode.

        If the mode is already expired, return None. Also return None if the course does not have a verified
        course mode.

        Returns:
            datetime|None
        """
        try:
            if self.verified_mode:
                log.debug('Schedules: Defaulting to verified mode expiration date-time for %s.', self.course_id)
                return self.verified_mode.expiration_datetime
            else:
                log.debug('Schedules: No verified mode located for %s.', self.course_id)
                return None
        except CourseMode.DoesNotExist:
            log.debug('Schedules: %s has no verified mode.', self.course_id)
            return None

    def is_verified_enrollment(self):
        """
        Check the course enrollment mode is verified or not
        """
        return CourseMode.is_verified_slug(self.mode)

    def is_professional_enrollment(self):
        """
        Check the course enrollment mode is professional or not
        """
        return CourseMode.is_professional_slug(self.mode)

    @classmethod
    def is_enrolled_as_verified(cls, user, course_key):
        """
        Check whether the course enrollment is for a verified mode.

        Arguments:
            user (User): The user object.
            course_key (CourseKey): The identifier for the course.

        Returns: bool

        """
        enrollment = cls.get_enrollment(user, course_key)
        return (
            enrollment is not None and
            enrollment.is_active and
            enrollment.is_verified_enrollment()
        )

    @classmethod
    def cache_key_name(cls, user_id, course_key):
        """Return cache key name to be used to cache current configuration.
        Args:
            user_id(int): Id of user.
            course_key(unicode): Unicode of course key

        Returns:
            Unicode cache key
        """
        return cls.COURSE_ENROLLMENT_CACHE_KEY.format(user_id, str(course_key))

    @classmethod
    def _get_enrollment_state(cls, user, course_key):
        """
        Returns the CourseEnrollmentState for the given user
        and course_key, caching the result for later retrieval.
        """
        assert user

        if user.is_anonymous:
            return CourseEnrollmentState(None, None)
        enrollment_state = cls._get_enrollment_in_request_cache(user, course_key)
        if not enrollment_state:
            try:
                record = cls.objects.get(user=user, course_id=course_key)
                enrollment_state = CourseEnrollmentState(record.mode, record.is_active)
            except cls.DoesNotExist:
                enrollment_state = CourseEnrollmentState(None, None)
            cls._update_enrollment_in_request_cache(user, course_key, enrollment_state)
        return enrollment_state

    @classmethod
    def bulk_fetch_enrollment_states(cls, users, course_key):
        """
        Bulk pre-fetches the enrollment states for the given users
        for the given course.
        """
        # before populating the cache with another bulk set of data,
        # remove previously cached entries to keep memory usage low.
        RequestCache(cls.MODE_CACHE_NAMESPACE).clear()

        records = cls.objects.filter(user__in=users, course_id=course_key).select_related('user')
        cache = cls._get_mode_active_request_cache()  # lint-amnesty, pylint: disable=redefined-outer-name
        for record in records:
            enrollment_state = CourseEnrollmentState(record.mode, record.is_active)
            cls._update_enrollment(cache, record.user.id, course_key, enrollment_state)

    @classmethod
    def _get_mode_active_request_cache(cls):
        """
        Returns the request-specific cache for CourseEnrollment as dict.
        """
        return RequestCache(cls.MODE_CACHE_NAMESPACE).data

    @classmethod
    def _get_enrollment_in_request_cache(cls, user, course_key):
        """
        Returns the cached value (CourseEnrollmentState) for the user's
        enrollment in the request cache.  If not cached, returns None.
        """
        return cls._get_mode_active_request_cache().get((user.id, course_key))

    @classmethod
    def _update_enrollment_in_request_cache(cls, user, course_key, enrollment_state):
        """
        Updates the cached value for the user's enrollment in the
        request cache.
        """
        cls._update_enrollment(cls._get_mode_active_request_cache(), user.id, course_key, enrollment_state)

    @classmethod
    def _update_enrollment(cls, cache, user_id, course_key, enrollment_state):  # lint-amnesty, pylint: disable=redefined-outer-name
        """
        Updates the cached value for the user's enrollment in the
        given cache.
        """
        cache[(user_id, course_key)] = enrollment_state

    @classmethod
    def get_active_enrollments_in_course(cls, course_key):
        """
        Retrieves active CourseEnrollments for a given course and
        prefetches user information.
        """
        return cls.objects.filter(
            course_id=course_key,
            is_active=True,
        ).select_related(
            'user',
            'user__profile',
        )


class FBEEnrollmentExclusion(models.Model):
    """
    Disable FBE for enrollments in this table.

    .. no_pii:
    """
    enrollment = models.OneToOneField(
        CourseEnrollment,
        on_delete=models.DO_NOTHING,
    )

    def __str__(self):
        return f"[FBEEnrollmentExclusion] {self.enrollment}"


@receiver(models.signals.post_save, sender=CourseEnrollment)
@receiver(models.signals.post_delete, sender=CourseEnrollment)
def invalidate_enrollment_mode_cache(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    Invalidate the cache of CourseEnrollment model.
    """

    cache_key = CourseEnrollment.cache_key_name(
        instance.user.id,
        str(instance.course_id)
    )
    cache.delete(cache_key)


@receiver(models.signals.post_save, sender=CourseEnrollment)
def update_expiry_email_date(sender, instance, **kwargs):  # pylint: disable=unused-argument
    """
    If the user has enrolled in verified track of a course and has expired ID
    verification then send email to get the ID verified by setting the
    expiry_email_date field.
    """
    email_config = getattr(settings, 'VERIFICATION_EXPIRY_EMAIL', {'DAYS_RANGE': 1, 'RESEND_DAYS': 15})

    if instance.mode == CourseMode.VERIFIED:
        SoftwareSecurePhotoVerification.update_expiry_email_date_for_user(instance.user, email_config)


class ManualEnrollmentAudit(models.Model):
    """
    Table for tracking which enrollments were performed through manual enrollment.

    .. pii: Contains enrolled_email, retired in LMSAccountRetirementView
    .. pii_types: email_address
    .. pii_retirement: local_api
    """
    enrollment = models.ForeignKey(CourseEnrollment, null=True, on_delete=models.CASCADE)
    enrolled_by = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    enrolled_email = models.CharField(max_length=255, db_index=True)
    time_stamp = models.DateTimeField(auto_now_add=True, null=True)
    state_transition = models.CharField(max_length=255, choices=TRANSITION_STATES)
    reason = models.TextField(null=True)
    role = models.CharField(blank=True, null=True, max_length=64)
    history = HistoricalRecords()

    @classmethod
    def create_manual_enrollment_audit(cls, user, email, state_transition, reason, enrollment=None, role=None):
        """
        saves the student manual enrollment information
        """
        return cls.objects.create(
            enrolled_by=user,
            enrolled_email=email,
            state_transition=state_transition,
            reason=reason,
            enrollment=enrollment,
            role=role,
        )

    @classmethod
    def get_manual_enrollment_by_email(cls, email):
        """
        if matches returns the most recent entry in the table filtered by email else returns None.
        """
        try:
            manual_enrollment = cls.objects.filter(enrolled_email=email).latest('time_stamp')
        except cls.DoesNotExist:
            manual_enrollment = None
        return manual_enrollment

    @classmethod
    def get_manual_enrollment(cls, enrollment):
        """
        Returns the most recent entry for the given enrollment, or None if there are no matches
        """
        try:
            manual_enrollment = cls.objects.filter(enrollment=enrollment).latest('time_stamp')
        except cls.DoesNotExist:
            manual_enrollment = None
        return manual_enrollment

    @classmethod
    def retire_manual_enrollments(cls, user, retired_email):
        """
        Removes PII (enrolled_email and reason) associated with the User passed in. Bubbles up any exceptions.
        """
        # This bit of ugliness is to fix a perfmance issue with Django using a slow
        # sub-select that caused the original query to take several seconds (PLAT-2371).
        # It is possible that this could also be bad if a user has thousands of manual
        # enrollments, but currently that number tends to be very low.
        manual_enrollment_ids = list(cls.objects.filter(enrollment__user=user).values_list('id', flat=True))
        manual_enrollment_audits = cls.objects.filter(id__in=manual_enrollment_ids)

        if not manual_enrollment_audits:
            return False

        for manual_enrollment_audit in manual_enrollment_audits:
            manual_enrollment_audit.history.update(reason="", enrolled_email=retired_email)
        manual_enrollment_audits.update(reason="", enrolled_email=retired_email)
        return True


class CourseEnrollmentAllowed(DeletableByUserValue, models.Model):
    """
    Table of users (specified by email address strings) who are allowed to enroll in a specified course.
    The user may or may not (yet) exist.  Enrollment by users listed in this table is allowed
    even if the enrollment time window is past.  Once an enrollment from this list effectively happens,
    the object is marked with the student who enrolled, to prevent students from changing e-mails and
    enrolling many accounts through the same e-mail.

    .. no_pii:
    """
    email = models.CharField(max_length=255, db_index=True)
    course_id = CourseKeyField(max_length=255, db_index=True)
    auto_enroll = models.BooleanField(default=0)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        help_text="First user which enrolled in the specified course through the specified e-mail. "
                  "Once set, it won't change.",
        on_delete=models.CASCADE,
    )

    created = models.DateTimeField(auto_now_add=True, null=True, db_index=True)

    class Meta:
        unique_together = (('email', 'course_id'),)

    def __str__(self):
        return f"[CourseEnrollmentAllowed] {self.email}: {self.course_id} ({self.created})"

    @classmethod
    def for_user(cls, user):
        """
        Returns the CourseEnrollmentAllowed objects that can effectively be used by a particular `user`.
        This includes the ones that match the user's e-mail and excludes those CEA which were already consumed
        by a different user.
        """
        return cls.objects.filter(email=user.email).filter(Q(user__isnull=True) | Q(user=user))

    def valid_for_user(self, user):
        """
        Returns True if the CEA is usable by the given user, or False if it was already consumed by another user.
        """
        return self.user is None or self.user == user

    @classmethod
    def may_enroll_and_unenrolled(cls, course_id):
        """
        Return QuerySet of students who are allowed to enroll in a course.

        Result excludes students who have already enrolled in the
        course.

        `course_id` identifies the course for which to compute the QuerySet.
        """
        enrolled = CourseEnrollment.objects.users_enrolled_in(course_id=course_id).values_list('email', flat=True)
        return CourseEnrollmentAllowed.objects.filter(course_id=course_id).exclude(email__in=enrolled)


@total_ordering
class CourseAccessRole(models.Model):
    """
    Maps users to org, courses, and roles. Used by student.roles.CourseRole and OrgRole.
    To establish a user as having a specific role over all courses in the org, create an entry
    without a course_id.

    .. no_pii:
    """

    objects = NoneToEmptyManager()

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # blank org is for global group based roles such as course creator (may be deprecated)
    org = models.CharField(max_length=64, db_index=True, blank=True)
    # blank course_id implies org wide role
    course_id = CourseKeyField(max_length=255, db_index=True, blank=True)
    role = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = ('user', 'org', 'course_id', 'role')

    @property
    def _key(self):
        """
        convenience function to make eq overrides easier and clearer. arbitrary decision
        that role is primary, followed by org, course, and then user
        """
        return (self.role, self.org, self.course_id, self.user_id)

    @classmethod
    def access_roles_in_course(cls, course_key):
        """
        Returns all CourseAccessRole for a given course and prefetches user information.
        """
        return cls.objects.filter(
            course_id=course_key,
        ).select_related(
            'user',
            'user__profile'
        )

    def __eq__(self, other):
        """
        Overriding eq b/c the django impl relies on the primary key which requires fetch. sometimes we
        just want to compare roles w/o doing another fetch.
        """
        return type(self) == type(other) and self._key == other._key  # lint-amnesty, pylint: disable=protected-access, unidiomatic-typecheck

    def __hash__(self):
        return hash(self._key)

    def __lt__(self, other):
        """
        Lexigraphic sort
        """
        return self._key < other._key

    def __str__(self):
        return f"[CourseAccessRole] user: {self.user.username}   role: {self.role}   org: {self.org}   course: {self.course_id}"  # lint-amnesty, pylint: disable=line-too-long


#### Helper methods for use from python manage.py shell and other classes.


def strip_if_string(value):
    if isinstance(value, str):
        return value.strip()
    return value


def get_user_by_username_or_email(username_or_email):
    """
    Return a User object by looking up a user against username_or_email.

    Raises:
        User.DoesNotExist if no user object can be found, the user was
        retired, or the user is in the process of being retired.

        MultipleObjectsReturned if one user has same email as username of
        second user

        MultipleObjectsReturned if more than one user has same email or
        username
    """
    username_or_email = strip_if_string(username_or_email)
    # there should be one user with either username or email equal to username_or_email
    user = User.objects.get(Q(email=username_or_email) | Q(username=username_or_email))
    if user.username == username_or_email:
        UserRetirementRequest = apps.get_model('user_api', 'UserRetirementRequest')
        if UserRetirementRequest.has_user_requested_retirement(user):
            raise User.DoesNotExist
    return user


def get_user(email):
    user = User.objects.get(email=email)
    u_prof = UserProfile.objects.get(user=user)
    return user, u_prof


def user_info(email):  # lint-amnesty, pylint: disable=missing-function-docstring
    user, u_prof = get_user(email)
    print("User id", user.id)
    print("Username", user.username)
    print("E-mail", user.email)
    print("Name", u_prof.name)
    print("Location", u_prof.location)
    print("Language", u_prof.language)
    return user, u_prof


def change_email(old_email, new_email):
    user = User.objects.get(email=old_email)
    user.email = new_email
    user.save()


def change_name(email, new_name):
    _user, u_prof = get_user(email)
    u_prof.name = new_name
    u_prof.save()


def user_count():
    print("All users", User.objects.all().count())
    print("Active users", User.objects.filter(is_active=True).count())
    return User.objects.all().count()


def active_user_count():
    return User.objects.filter(is_active=True).count()


def create_group(name, description):
    utg = UserTestGroup()
    utg.name = name
    utg.description = description
    utg.save()


def add_user_to_group(user, group):
    utg = UserTestGroup.objects.get(name=group)
    utg.users.add(User.objects.get(username=user))
    utg.save()


def remove_user_from_group(user, group):
    utg = UserTestGroup.objects.get(name=group)
    utg.users.remove(User.objects.get(username=user))
    utg.save()

DEFAULT_GROUPS = {
    'email_future_courses': 'Receive e-mails about future MITx courses',
    'email_helpers': 'Receive e-mails about how to help with MITx',
    'mitx_unenroll': 'Fully unenrolled -- no further communications',
    '6002x_unenroll': 'Took and dropped 6002x'
}


def add_user_to_default_group(user, group):  # lint-amnesty, pylint: disable=missing-function-docstring
    try:
        utg = UserTestGroup.objects.get(name=group)
    except UserTestGroup.DoesNotExist:
        utg = UserTestGroup()
        utg.name = group
        utg.description = DEFAULT_GROUPS[group]
        utg.save()
    utg.users.add(User.objects.get(username=user))
    utg.save()


def create_comments_service_user(user):  # lint-amnesty, pylint: disable=missing-function-docstring
    if not settings.FEATURES['ENABLE_DISCUSSION_SERVICE']:
        # Don't try--it won't work, and it will fill the logs with lots of errors
        return
    try:
        cc_user = cc.User.from_django_user(user)
        cc_user.save()
    except Exception:  # pylint: disable=broad-except
        log = logging.getLogger("edx.discussion")  # pylint: disable=redefined-outer-name
        log.error(
            f"Could not create comments service user with id {user.id}",
            exc_info=True
        )

# Define login and logout handlers here in the models file, instead of the views file,
# so that they are more likely to be loaded when a Studio user brings up the Studio admin
# page to login.  These are currently the only signals available, so we need to continue
# identifying and logging failures separately (in views).


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):  # lint-amnesty, pylint: disable=unused-argument
    """Handler to log when logins have occurred successfully."""
    if settings.FEATURES['SQUELCH_PII_IN_LOGS']:
        AUDIT_LOG.info(f"Login success - user.id: {user.id}")
    else:
        AUDIT_LOG.info(f"Login success - {user.username} ({user.email})")


@receiver(user_logged_out)
def log_successful_logout(sender, request, user, **kwargs):  # lint-amnesty, pylint: disable=unused-argument
    """Handler to log when logouts have occurred successfully."""
    if hasattr(request, 'user'):
        if settings.FEATURES['SQUELCH_PII_IN_LOGS']:
            AUDIT_LOG.info(f'Logout - user.id: {request.user.id}')  # pylint: disable=logging-format-interpolation
        else:
            AUDIT_LOG.info(f'Logout - {request.user}')  # pylint: disable=logging-format-interpolation
        if request.user.id:
            segment.track(request.user.id, 'edx.bi.user.account.logout')


@receiver(user_logged_in)
@receiver(user_logged_out)
def enforce_single_login(sender, request, user, signal, **kwargs):  # pylint: disable=unused-argument
    """
    Sets the current session id in the user profile,
    to prevent concurrent logins.
    """
    if settings.FEATURES.get('PREVENT_CONCURRENT_LOGINS', False):
        if signal == user_logged_in:
            key = request.session.session_key
        else:
            key = None
        if user:
            user_profile, __ = UserProfile.objects.get_or_create(
                user=user,
                defaults={'name': user.username}
            )
            if user_profile:
                user.profile.set_login_session(key)


class DashboardConfiguration(ConfigurationModel):
    """
    Note:
        This model is deprecated and we should not be adding new content to it.
        We will eventually migrate this one entry to a django setting as well.

    Dashboard Configuration settings.

    Includes configuration options for the dashboard, which impact behavior and rendering for the application.

    .. no_pii:
    """
    recent_enrollment_time_delta = models.PositiveIntegerField(
        default=0,
        help_text="The number of seconds in which a new enrollment is considered 'recent'. "
                  "Used to display notifications."
    )

    @property
    def recent_enrollment_seconds(self):
        return self.recent_enrollment_time_delta


class LinkedInAddToProfileConfiguration(ConfigurationModel):
    """
    LinkedIn Add to Profile Configuration

    This configuration enables the 'Add to Profile' LinkedIn button. The button
    appears when users have a certificate available; when clicked, users are sent
    to the LinkedIn site with a pre-filled form allowing them to add the
    certificate to their LinkedIn profile.

    See https://addtoprofile.linkedin.com/ for documentation on parameters

    .. no_pii:
    """

    MODE_TO_CERT_NAME = {
        'honor': _('{platform_name} Honor Code Certificate for {course_name}'),
        'verified': _('{platform_name} Verified Certificate for {course_name}'),
        'professional': _('{platform_name} Professional Certificate for {course_name}'),
        'no-id-professional': _('{platform_name} Professional Certificate for {course_name}'),
    }

    company_identifier = models.TextField(
        blank=True,
        help_text=_(
            'Your organization ID (if your organization has an existing page on LinkedIn) e.g 1337. '
            'If not provided, will default to sending Platform Name (e.g. edX) instead.'
        ),
    )

    def is_enabled(self, *key_fields):  # pylint: disable=arguments-differ
        """
        Checks both the model itself and share_settings to see if LinkedIn Add to Profile is enabled
        """
        enabled = super().is_enabled(*key_fields)
        share_settings = configuration_helpers.get_value('SOCIAL_SHARING_SETTINGS', settings.SOCIAL_SHARING_SETTINGS)
        return share_settings.get('CERTIFICATE_LINKEDIN', enabled)

    def add_to_profile_url(self, course_name, cert_mode, cert_url, certificate=None):
        """
        Construct the URL for the "add to profile" button. This will autofill the form based on
        the params provided.

        Arguments:
            course_name (str): The display name of the course.
            cert_mode (str): The course mode of the user's certificate (e.g. "verified", "honor", "professional")
            cert_url (str): The URL for the certificate.

        Keyword Arguments:
            certificate (GeneratedCertificate): a GeneratedCertificate object for the user and course.
                If provided, this function will also autofill the certId and issue date for the cert.
        """
        params = {
            'name': self._cert_name(course_name, cert_mode),
            'certUrl': cert_url,
        }

        params.update(self._organization_information())

        if certificate:
            params.update({
                'certId': certificate.verify_uuid,
                'issueYear': certificate.created_date.year,
                'issueMonth': certificate.created_date.month,
            })

        return 'https://www.linkedin.com/profile/add?startTask=CERTIFICATION_NAME&{params}'.format(
            params=urlencode(params)
        )

    def _cert_name(self, course_name, cert_mode):
        """
        Name of the certification, for display on LinkedIn.

        Arguments:
            course_name (unicode): The display name of the course.
            cert_mode (str): The course mode of the user's certificate (e.g. "verified", "honor", "professional")

        Returns:
            str: The formatted string to display for the name field on the LinkedIn Add to Profile dialog.
        """
        default_cert_name = self.MODE_TO_CERT_NAME.get(cert_mode, _('{platform_name} Certificate for {course_name}'))
        # Look for an override of the certificate name in the SOCIAL_SHARING_SETTINGS setting
        share_settings = configuration_helpers.get_value('SOCIAL_SHARING_SETTINGS', settings.SOCIAL_SHARING_SETTINGS)
        cert_name = share_settings.get('CERTIFICATE_LINKEDIN_MODE_TO_CERT_NAME', {}).get(cert_mode, default_cert_name)

        return cert_name.format(
            platform_name=configuration_helpers.get_value('platform_name', settings.PLATFORM_NAME),
            course_name=course_name
        )

    def _organization_information(self):
        """
        Returns organization information for use in the URL parameters for add to profile.

        Returns:
            dict: Either the organization ID on LinkedIn or the organization's name
                Will be used to prefill the organization on the add to profile action.
        """
        org_id = configuration_helpers.get_value('LINKEDIN_COMPANY_ID', self.company_identifier)
        # Prefer organization ID per documentation at https://addtoprofile.linkedin.com/
        if org_id:
            return {'organizationId': org_id}
        return {'organizationName': configuration_helpers.get_value('platform_name', settings.PLATFORM_NAME)}


class EntranceExamConfiguration(models.Model):
    """
    Represents a Student's entrance exam specific data for a single Course

    .. no_pii:
    """

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    course_id = CourseKeyField(max_length=255, db_index=True)
    created = models.DateTimeField(auto_now_add=True, null=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)

    # if skip_entrance_exam is True, then student can skip entrance exam
    # for the course
    skip_entrance_exam = models.BooleanField(default=True)

    class Meta:
        unique_together = (('user', 'course_id'), )

    def __str__(self):
        return "[EntranceExamConfiguration] {}: {} ({}) = {}".format(
            self.user, self.course_id, self.created, self.skip_entrance_exam
        )

    @classmethod
    def user_can_skip_entrance_exam(cls, user, course_key):
        """
        Return True if given user can skip entrance exam for given course otherwise False.
        """
        can_skip = False
        if ENTRANCE_EXAMS.is_enabled():
            try:
                record = EntranceExamConfiguration.objects.get(user=user, course_id=course_key)
                can_skip = record.skip_entrance_exam
            except EntranceExamConfiguration.DoesNotExist:
                can_skip = False
        return can_skip


class LanguageField(models.CharField):
    """Represents a language from the ISO 639-1 language set."""

    def __init__(self, *args, **kwargs):
        """Creates a LanguageField.

        Accepts all the same kwargs as a CharField, except for max_length and
        choices. help_text defaults to a description of the ISO 639-1 set.
        """
        kwargs.pop('max_length', None)
        kwargs.pop('choices', None)
        help_text = kwargs.pop(
            'help_text',
            _("The ISO 639-1 language code for this language."),
        )
        super().__init__(
            max_length=16,
            choices=settings.ALL_LANGUAGES,
            help_text=help_text,
            *args,
            **kwargs
        )


class LanguageProficiency(models.Model):
    """
    Represents a user's language proficiency.

    Note that we have not found a way to emit analytics change events by using signals directly on this
    model or on UserProfile. Therefore if you are changing LanguageProficiency values, it is important
    to go through the accounts API (AccountsView) defined in
    /edx-platform/openedx/core/djangoapps/user_api/accounts/views.py or its associated api method
    (update_account_settings) so that the events are emitted.

    .. no_pii: Language is not PII value according to OEP-30.
    """
    class Meta:
        unique_together = (('code', 'user_profile'),)

    user_profile = models.ForeignKey(UserProfile, db_index=True, related_name='language_proficiencies',
                                     on_delete=models.CASCADE)
    code = models.CharField(
        max_length=16,
        blank=False,
        choices=settings.ALL_LANGUAGES,
        help_text=_("The ISO 639-1 language code for this language.")
    )


class SocialLink(models.Model):
    """
    Represents a URL connecting a particular social platform to a user's social profile.

    The platforms are listed in the lms/common.py file under SOCIAL_PLATFORMS.
    Each entry has a display name, a url_stub that describes a required
    component of the stored URL and an example of a valid URL.

    The stored social_link value must adhere to the form 'https://www.[url_stub][username]'.

    .. pii: Stores linkage from User to a learner's social media profiles. Retired in AccountRetirementView.
    .. pii_types: external_service
    .. pii_retirement: local_api
    """
    user_profile = models.ForeignKey(UserProfile, db_index=True, related_name='social_links', on_delete=models.CASCADE)
    platform = models.CharField(max_length=30)
    social_link = models.CharField(max_length=100, blank=True)


class CourseEnrollmentAttribute(models.Model):
    """
    Provide additional information about the user's enrollment.

    .. no_pii: This stores key/value pairs, of which there is no full list, but the ones currently in use are not PII
    """
    enrollment = models.ForeignKey(CourseEnrollment, related_name="attributes", on_delete=models.CASCADE)
    namespace = models.CharField(
        max_length=255,
        help_text=_("Namespace of enrollment attribute")
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the enrollment attribute")
    )
    value = models.CharField(
        max_length=255,
        help_text=_("Value of the enrollment attribute")
    )

    def __str__(self):
        """Unicode representation of the attribute. """
        return "{namespace}:{name}, {value}".format(
            namespace=self.namespace,
            name=self.name,
            value=self.value,
        )

    @classmethod
    def add_enrollment_attr(cls, enrollment, data_list):
        """
        Delete all the enrollment attributes for the given enrollment and
        add new attributes.

        Args:
            enrollment (CourseEnrollment): 'CourseEnrollment' for which attribute is to be added
            data_list: list of dictionaries containing data to save
        """
        cls.objects.filter(enrollment=enrollment).delete()
        attributes = [
            cls(enrollment=enrollment, namespace=data['namespace'], name=data['name'], value=data['value'])
            for data in data_list
        ]
        cls.objects.bulk_create(attributes)

    @classmethod
    def get_enrollment_attributes(cls, enrollment):
        """Retrieve list of all enrollment attributes.

        Args:
            enrollment(CourseEnrollment): 'CourseEnrollment' for which list is to retrieve

        Returns: list

        Example:
        >>> CourseEnrollmentAttribute.get_enrollment_attributes(CourseEnrollment)
        [
            {
                "namespace": "credit",
                "name": "provider_id",
                "value": "hogwarts",
            },
        ]
        """
        return [
            {
                "namespace": attribute.namespace,
                "name": attribute.name,
                "value": attribute.value,
            }
            for attribute in cls.objects.filter(enrollment=enrollment)
        ]


class EnrollmentRefundConfiguration(ConfigurationModel):
    """
    Configuration for course enrollment refunds.

    .. no_pii:
    """

    # TODO: Django 1.8 introduces a DurationField
    # (https://docs.djangoproject.com/en/1.8/ref/models/fields/#durationfield)
    # for storing timedeltas which uses MySQL's bigint for backing
    # storage. After we've completed the Django upgrade we should be
    # able to replace this field with a DurationField named
    # `refund_window` without having to run a migration or change
    # other code.
    refund_window_microseconds = models.BigIntegerField(
        default=1209600000000,
        help_text=_(
            "The window of time after enrolling during which users can be granted"
            " a refund, represented in microseconds. The default is 14 days."
        )
    )

    @property
    def refund_window(self):
        """Return the configured refund window as a `datetime.timedelta`."""
        return timedelta(microseconds=self.refund_window_microseconds)

    @refund_window.setter
    def refund_window(self, refund_window):
        """Set the current refund window to the given timedelta."""
        self.refund_window_microseconds = int(refund_window.total_seconds() * 1000000)


class RegistrationCookieConfiguration(ConfigurationModel):
    """
    Configuration for registration cookies.

    .. no_pii:
    """
    utm_cookie_name = models.CharField(
        max_length=255,
        help_text=_("Name of the UTM cookie")
    )

    affiliate_cookie_name = models.CharField(
        max_length=255,
        help_text=_("Name of the affiliate cookie")
    )

    def __str__(self):
        """Unicode representation of this config. """
        return "UTM: {utm_name}; AFFILIATE: {affiliate_name}".format(
            utm_name=self.utm_cookie_name,
            affiliate_name=self.affiliate_cookie_name
        )


class BulkUnenrollConfiguration(ConfigurationModel):  # lint-amnesty, pylint: disable=empty-docstring
    """

    """
    csv_file = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_("It expect that the data will be provided in a csv file format with \
                    first row being the header and columns will be as follows: \
                    user_id, username, email, course_id, is_verified, verification_date")
    )


class BulkChangeEnrollmentConfiguration(ConfigurationModel):
    """
    config model for the bulk_change_enrollment_csv command
    """
    csv_file = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_("It expect that the data will be provided in a csv file format with \
                    first row being the header and columns will be as follows: \
                    course_id, username, mode")
    )


class UserAttribute(TimeStampedModel):
    """
    Record additional metadata about a user, stored as key/value pairs of text.

    .. no_pii:
    """

    class Meta:
        # Ensure that at most one value exists for a given user/name.
        unique_together = (('user', 'name',), )

    user = models.ForeignKey(User, related_name='attributes', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, help_text=_("Name of this user attribute."), db_index=True)
    value = models.CharField(max_length=255, help_text=_("Value of this user attribute."))

    def __str__(self):
        return "[{username}] {name}: {value}".format(
            name=self.name,
            value=self.value,
            username=self.user.username
        )

    @classmethod
    def set_user_attribute(cls, user, name, value):
        """
        Add an name/value pair as an attribute for the given
        user. Overwrites any previous value for that name, if it
        exists.
        """
        cls.objects.update_or_create(user=user, name=name, defaults={'value': value})

    @classmethod
    def get_user_attribute(cls, user, name):
        """
        Return the attribute value for the given user and name. If no such
        value exists, returns None.
        """
        try:
            return cls.objects.get(user=user, name=name).value
        except cls.DoesNotExist:
            return None


class AccountRecoveryManager(models.Manager):
    """
    Custom Manager for AccountRecovery model
    """

    def get_active(self, **filters):
        """
        Return only active AccountRecovery record after applying the given filters.

        Arguments:
            filters (**kwargs): Filter parameters for AccountRecovery records.

        Returns:
            AccountRecovery: AccountRecovery object with is_active=true
        """
        filters['is_active'] = True
        return super().get_queryset().get(**filters)

    def activate(self):
        """
        Set is_active flag to True.
        """
        super().get_queryset().update(is_active=True)


class AccountRecovery(models.Model):
    """
    Model for storing information for user's account recovery in case of access loss.

    .. pii: the field named secondary_email contains pii, retired in the `DeactivateLogoutView`
    .. pii_types: email_address
    .. pii_retirement: local_api
    """
    user = models.OneToOneField(User, related_name='account_recovery', on_delete=models.CASCADE)
    secondary_email = models.EmailField(
        verbose_name=_('Secondary email address'),
        help_text=_('Secondary email address to recover linked account.'),
        unique=True,
        null=False,
        blank=False,
    )
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "auth_accountrecovery"

    objects = AccountRecoveryManager()

    def update_recovery_email(self, email):
        """
        Update the secondary email address on the instance to the email in the argument.

        Arguments:
            email (str): New email address to be set as the secondary email address.
        """
        self.secondary_email = email
        self.is_active = True
        self.save()

    @classmethod
    def retire_recovery_email(cls, user_id):
        """
        Retire user's recovery/secondary email as part of GDPR Phase I.
        Returns 'True'

        If an AccountRecovery record is found for this user it will be deleted,
        if it is not found it is assumed this table has no PII for the given user.

        :param user_id: int
        :return: bool
        """
        try:
            cls.objects.get(user_id=user_id).delete()
        except cls.DoesNotExist:
            pass

        return True


class AllowedAuthUser(TimeStampedModel):
    site = models.ForeignKey(Site, related_name='allowed_auth_users', on_delete=models.CASCADE)
    email = models.EmailField(
        help_text=_(
            "An employee (a user whose email has current site's domain name) whose email exists in this model, can be "
            "able to login from login screen through email and password. And if any employee's email doesn't exist in "
            "this model then that employee can login via third party authentication backend only."),
        unique=True,
    )


class AccountRecoveryConfiguration(ConfigurationModel):
    """
    configuration model for recover account management command
    """
    csv_file = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text=_("It expect that the data will be provided in a csv file format with \
                    first row being the header and columns will be as follows: \
                    username, current_email, desired_email")
    )


class UserCelebration(TimeStampedModel):
    """
    Keeps track of how we've celebrated a user's progress on the platform.
    This class is for course agnostic celebrations (not specific to a particular enrollment).
    CourseEnrollmentCelebration is for celebrations that happen separately for each separate course.

    .. no_pii:
    """
    user = models.OneToOneField(User, models.CASCADE, related_name='celebration')
    # The last_day_of_streak and streak_length fields are used to
    # control celebration of the streak feature.
    # A streak is when a learner visits the learning MFE N days in a row.
    # The business logic of streaks for a 3 day streak and 1 day break is the following:
    # 1. Each streak should be celebrated exactly once, once the learner has completed the streak.
    # 2. If a learner misses enough days to count as a break, the streak resets back to 0.
    # 3. The streak is measured against the learner's configured timezone
    # 4. We keep track of the total length of the streak, so there is a possibility in the future
    # to add multiple celebrations for longer streaks.
    # 5. We keep track of the longest_ever_streak field for potential future use for badging purposes.
    last_day_of_streak = models.DateField(default=None, null=True, blank=True)
    streak_length = models.IntegerField(default=0)
    longest_ever_streak = models.IntegerField(default=0)
    STREAK_LENGTHS_TO_CELEBRATE = [3]
    STREAK_BREAK_LENGTH = 1

    def __str__(self):
        return (
            '[UserCelebration] user: {}; last_day_of_streak {}; streak_length {}; longest_ever_streak {};'
        ).format(self.user.username, self.last_day_of_streak, self.streak_length, self.longest_ever_streak)

    @classmethod
    def _get_now(cls, browser_timezone):
        """ Retrieve the value for the current datetime in the user's timezone

        Once a user visits the learning MFE, their streak will not increment until midnight in their timezone.
        The decision was to use the user's timezone and not UTC, to make each day of the streak more closely
        correspond to separate days for the user.
        The learning MFE passes in the browser timezone which is used as a fallback option if the user's timezone
        in their account is not set.
        UTC is used as a final fallback if neither timezone is set.
        """
        # importing here to avoid a circular import
        from lms.djangoapps.courseware.context_processor import user_timezone_locale_prefs
        user_timezone_locale = user_timezone_locale_prefs(crum.get_current_request())
        user_timezone = timezone(user_timezone_locale['user_timezone'] or browser_timezone or str(UTC))
        return user_timezone.localize(datetime.now())

    def _calculate_streak_updates(self, today):
        """ Calculate the updates that should be applied to the streak fields of the provided celebration
        A streak is incremented once for each day that a learner accesses the learning MFE.
        A break is the amount of time that needs to pass before we stop incrementing the
        existing streak and start a brand new streak.
        See the UserCelebrationTests class for examples that should help clarify this behavior.
        """
        last_day_of_streak = self.last_day_of_streak
        streak_length = self.streak_length
        streak_length_to_celebrate = None

        first_ever_streak = last_day_of_streak is None
        break_length = timedelta(days=self.STREAK_BREAK_LENGTH)
        should_start_new_streak = last_day_of_streak and last_day_of_streak + break_length < today
        already_updated_streak_today = last_day_of_streak == today

        last_day_of_streak = today
        if first_ever_streak or should_start_new_streak:
            # Start new streak
            streak_length = 1
        elif not already_updated_streak_today:
            streak_length += 1
            if streak_length in self.STREAK_LENGTHS_TO_CELEBRATE:
                # Celebrate if we didn't already celebrate today
                streak_length_to_celebrate = streak_length

        return last_day_of_streak, streak_length, streak_length_to_celebrate

    def _update_streak(self, last_day_of_streak, streak_length):
        """ Update the celebration with the new streak data """
        # If anything needs to be updated, update the celebration in the database
        if last_day_of_streak != self.last_day_of_streak:
            self.last_day_of_streak = last_day_of_streak
            self.streak_length = streak_length
            self.longest_ever_streak = max(self.longest_ever_streak, streak_length)

            self.save()

    @classmethod
    def _get_celebration(cls, user, course_key):
        """ Retrieve (or create) the celebration for the provided user and course_key """
        try:
            # Only enable the streak if milestones and the streak are enabled for this course
            if not streak_celebration_is_active(course_key):
                return None
            return user.celebration
        except (cls.DoesNotExist, User.celebration.RelatedObjectDoesNotExist):  # pylint: disable=no-member
            celebration, _ = UserCelebration.objects.get_or_create(user=user)
            return celebration

    @classmethod
    def perform_streak_updates(cls, user, course_key, browser_timezone=None):
        """ Determine if the user should see a streak celebration and
            return the length of the streak the user should celebrate.
            Also update the streak data that is stored in the database."""
        # importing here to avoid a circular import
        from lms.djangoapps.courseware.masquerade import is_masquerading_as_specific_student
        if not user or user.is_anonymous:
            return None

        if is_masquerading_as_specific_student(user, course_key):
            return None

        celebration = cls._get_celebration(user, course_key)

        if not celebration:
            return None

        today = cls._get_now(browser_timezone).date()

        # pylint: disable=protected-access
        last_day_of_streak, streak_length, streak_length_to_celebrate = \
            celebration._calculate_streak_updates(today)
        # pylint: enable=protected-access

        cls._update_streak(celebration, last_day_of_streak, streak_length)

        return streak_length_to_celebrate


class CourseEnrollmentCelebration(TimeStampedModel):
    """
    Keeps track of how we've celebrated a user's course progress.

    An example of a celebration is a dialog that pops up after you complete your first section
    in a course saying "good job!". Just some positive feedback like that. (This specific example is
    controlled by the celebrated_first_section field below.)

    In general, if a row does not exist for an enrollment, we don't want to show any celebrations.
    We don't want to suddenly inject celebrations in the middle of a course, because they
    might not make contextual sense and it's an inconsistent experience. The helper methods below
    (starting with "should_") can help by looking up values with appropriate fallbacks.

    See the create_course_enrollment_celebration signal handler for how these get created.

    .. no_pii:
    """
    enrollment = models.OneToOneField(CourseEnrollment, models.CASCADE, related_name='celebration')
    celebrate_first_section = models.BooleanField(default=False)
    celebrate_weekly_goal = models.BooleanField(default=False)

    def __str__(self):
        return (
            '[CourseEnrollmentCelebration] course: {}; user: {}'
        ).format(self.enrollment.course.id, self.enrollment.user.username)

    @staticmethod
    def should_celebrate_first_section(enrollment):
        """
        Returns the celebration value for first_section with appropriate fallback if it doesn't exist.

        The frontend will use this result and additional information calculated to actually determine
        if the first section celebration will render. In other words, the value returned here is
        NOT the final value used.
        """
        if not enrollment:
            return False
        try:
            return enrollment.celebration.celebrate_first_section
        except CourseEnrollmentCelebration.DoesNotExist:
            return False

    @staticmethod
    def should_celebrate_weekly_goal(enrollment):
        """
        Returns the celebration value for weekly_goal with appropriate fallback if it doesn't exist.

        The frontend will use this result directly to determine if the weekly goal celebration
        should be rendered. The value returned here IS the final value used.
        """
        # Avoiding circular import
        from lms.djangoapps.course_goals.models import CourseGoal, UserActivity
        try:
            if not enrollment or not enrollment.celebration.celebrate_weekly_goal:
                return False
        except CourseEnrollmentCelebration.DoesNotExist:
            return False

        try:
            goal = CourseGoal.objects.get(user=enrollment.user, course_key=enrollment.course.id)
            if not goal.days_per_week:
                return False

            today = date.today()
            monday_date = today - timedelta(days=today.weekday())
            week_activity_count = UserActivity.objects.filter(
                user=enrollment.user, course_key=enrollment.course.id, date__gte=monday_date,
            ).count()
            return week_activity_count == goal.days_per_week
        except CourseGoal.DoesNotExist:
            return False


class UserPasswordToggleHistory(TimeStampedModel):
    """
    Keeps track of user password disable/enable history
    """
    user = models.ForeignKey(User, related_name='password_toggle_history', on_delete=models.CASCADE)
    comment = models.CharField(max_length=255, help_text=_("Add a reason"), blank=True, null=True)
    disabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.comment
