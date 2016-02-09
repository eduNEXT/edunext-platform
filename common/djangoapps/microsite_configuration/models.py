"""
Model to store a microsite in the database.

The object is stored as a json representation of the python dict
that would have been used in the settings.

"""
import collections
import json

from django.db import models
from django.db.models.base import ObjectDoesNotExist
from django.core.exceptions import ValidationError

from jsonfield.fields import JSONField
from simple_history.models import HistoricalRecords


class Microsite(models.Model):
    """
    This is where the information about the microsite gets stored to the db.
    To achieve the maximum flexibility, most of the fields are stored inside
    a json field.

    Notes:
        - The key field was required for the dict definition at the settings, and it
        is used in some of the microsite_configuration methods.
        - The subdomain is outside of the json so that it is posible to use a db query
        to improve performance.
        - The values field must be validated on save to prevent the platform from crashing
        badly in the case the string is not able to be loaded as json.
    """
    key = models.CharField(max_length=63, db_index=True)
    subdomain = models.CharField(max_length=127, db_index=True)
    values = JSONField(null=False, blank=True, load_kwargs={'object_pairs_hook': collections.OrderedDict})

    def __unicode__(self):
        return self.key

    def get_organizations(self):
        """
        Helper method to return a list of organizations associated with our particular Microsite
        """
        # has to return the same type as:
        # MicrositeOrganizationMapping.get_organizations_for_microsite_by_pk(self.id)
        org_filter = self.values.get('course_org_filter')

        if isinstance(org_filter, basestring):
            org_filter = [org_filter]

        return org_filter

    @classmethod
    def get_microsite_for_domain(cls, domain):
        """
        Returns the microsite associated with this domain. Note that we always convert to lowercase, or
        None if no match
        """

        # remove any port number from the hostname
        domain = domain.split(':')[0]
        microsites = cls.objects.filter(subdomain=domain)

        return microsites[0] if microsites else None


class MicrositeOrganizationMapping(models.Model):
    """
    Mapping of Organization to which Microsite it belongs
    """

    organization = models.CharField(max_length=63, db_index=True, unique=True)
    microsite = models.ForeignKey(Microsite, db_index=True)

    # for archiving
    history = HistoricalRecords()

    def __unicode__(self):
        """String conversion"""
        return u'{microsite_key}: {organization}'.format(
            microsite_key=self.microsite.key,
            organization=self.organization
        )

    @classmethod
    def get_organizations_for_microsite_by_pk(cls, microsite_pk):
        """
        Returns a list of organizations associated with the microsite key, returned as a set
        """
        return cls.objects.filter(microsite_id=microsite_pk).values_list('organization', flat=True)

    @classmethod
    def get_microsite_for_organization(cls, org):
        """
        Returns the microsite object for a given organization based on the table mapping, None if
        no mapping exists
        """

        try:
            item = cls.objects.select_related('microsite').get(organization=org)
            return item.microsite
        except ObjectDoesNotExist:
            return None


class MicrositeTemplate(models.Model):
    """
    A HTML template that a microsite can use
    """

    microsite = models.ForeignKey(Microsite, db_index=True)
    template_uri = models.CharField(max_length=255, db_index=True)
    template = models.TextField()

    # for archiving
    history = HistoricalRecords()

    def __unicode__(self):
        """String conversion"""
        return u'{microsite_key}: {template_uri}'.format(
            microsite_key=self.microsite.key,
            template_uri=self.template_uri
        )

    class Meta(object):
        """ Meta class for this Django model """
        unique_together = (('microsite', 'template_uri'),)

    @classmethod
    def get_template_for_microsite(cls, domain, template_uri):
        """
        Returns the template object for the microsite, None if not found
        """
        try:
            return cls.objects.get(microsite__subdomain=domain, template_uri=template_uri)
        except ObjectDoesNotExist:
            return None
