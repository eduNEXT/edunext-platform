# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def join_courses_with_orgs(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    OrganizationCourse = apps.get_model("organizations", "OrganizationCourse")
    CourseOverview = apps.get_model("course_overviews", "CourseOverview")

    # Generating missing links between courses and orgs
    for c_obj in CourseOverview.objects.all():
        org_obj, _ = Organization.objects.get_or_create(short_name=c_obj.org)
        OrganizationCourse.objects.get_or_create(
            course_id=c_obj.id,
            organization=org_obj
        )


def backwards(apps, schema_editor):
    OrganizationCourse = apps.get_model("organizations", "OrganizationCourse")
    # Deleting all organization-course link records
    OrganizationCourse.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0004_microsites_orgs_migration'),
        ('course_overviews', '0005_delete_courseoverviewgeneratedhistory'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(join_courses_with_orgs, backwards),
    ]
