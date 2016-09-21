"""
Django admin page for microsite models
"""
from django.contrib import admin
from django import forms

from .models import (
    Microsite,
    MicrositeHistory,
    MicrositeOrganizationMapping,
    MicrositeTemplate
)
from util.organizations_helpers import get_organizations


class MicrositeAdmin(admin.ModelAdmin):
    """ Admin interface for the Microsite object. """
    list_display = ('key', 'site')
    search_fields = ('site__domain', 'values')

    class Meta(object):  # pylint: disable=missing-docstring
        model = Microsite


class MicrositeHistoryAdmin(admin.ModelAdmin):
    """ Admin interface for the MicrositeHistory object. """
    list_display = ('key', 'site', 'created')
    search_fields = ('site__domain', 'values')

    ordering = ['-created']

    class Meta(object):  # pylint: disable=missing-docstring
        model = MicrositeHistory

    def has_add_permission(self, request):
        """Don't allow adds"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletes"""
        return False


class MicrositeOrganizationMappingForm(forms.ModelForm):
    """
    Django admin form for MicrositeOrganizationMapping model
    """
    def __init__(self, *args, **kwargs):
        super(MicrositeOrganizationMappingForm, self).__init__(*args, **kwargs)
        organizations = get_organizations()
        org_choices = [(org["short_name"], org["name"]) for org in organizations]
        org_choices.insert(0, ('', 'None'))
        self.fields['organization'] = forms.TypedChoiceField(
            choices=org_choices, required=False, empty_value=None
        )

    class Meta(object):
        model = MicrositeOrganizationMapping
        fields = '__all__'


class MicrositeOrganizationMappingAdmin(admin.ModelAdmin):
    """ Admin interface for the MicrositeOrganizationMapping object. """
    list_display = ('organization', 'microsite')
    search_fields = ('organization', 'microsite')
    form = MicrositeOrganizationMappingForm

    class Meta(object):  # pylint: disable=missing-docstring
        model = MicrositeOrganizationMapping


class MicrositeTemplateAdmin(admin.ModelAdmin):
    """ Admin interface for the MicrositeTemplate object. """
    list_display = ('microsite', 'template_uri')
    search_fields = ('microsite', 'template_uri')

    class Meta(object):  # pylint: disable=missing-docstring
        model = MicrositeTemplate

admin.site.register(MicrositeHistory, MicrositeHistoryAdmin)
admin.site.register(MicrositeOrganizationMapping, MicrositeOrganizationMappingAdmin)
admin.site.register(MicrositeTemplate, MicrositeTemplateAdmin)


class EdunextMicrositeAdmin(admin.ModelAdmin):
    list_display = [
        'key',
        'subdomain',
        'sitename',
        'template_dir',
        'course_org_filter',
    ]
    readonly_fields = (
        'sitename',
        'template_dir',
        'course_org_filter',
    )
    search_fields = ('key', 'subdomain', 'values', )

    def sitename(self, microsite):
        try:
            return microsite.values.get('SITE_NAME', "NOT CONFIGURED")
        except Exception, e:
            return unicode(e)

    def template_dir(self, microsite):
        try:
            return microsite.values.get('template_dir', "NOT CONFIGURED")
        except Exception, e:
            return unicode(e)

    def course_org_filter(self, microsite):
        try:
            return microsite.values.get('course_org_filter', "NOT CONFIGURED")
        except Exception, e:
            return unicode(e)

admin.site.register(Microsite, EdunextMicrositeAdmin)
