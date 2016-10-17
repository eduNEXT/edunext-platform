# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def microsite_orgs_to_org_records(apps, schema_editor):
    Microsite = apps.get_model("microsite_configuration", "Microsite")
    Organization = apps.get_model("organizations", "Organization")

    # Getting all microsite orgs
    org_filter_set = set()
    candidates = Microsite.objects.all()
    for microsite in candidates:
        current = microsite.values
        org_filter = current.get('course_org_filter')
        if org_filter and type(org_filter) is list:
            for org in org_filter:
                org_filter_set.add(org)
        elif org_filter:
            org_filter_set.add(org_filter)

    # Creating new organization records
    for s_org in org_filter_set:
        org_obj, is_new = Organization.objects.get_or_create(
            short_name=s_org
        )
        # This is done to avoid org duplication with the same short name
        if is_new:
            org_obj.name = s_org
            org_obj.description = "Organization {}".format(s_org)
            org_obj.save()


def backwards(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    # Deleting all organization records
    Organization.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0002_auto_20160202_0228'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(microsite_orgs_to_org_records, backwards),
    ]
