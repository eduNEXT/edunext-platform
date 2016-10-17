# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields
import model_utils.fields
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0001_initial'),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MicrositeHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('key', models.CharField(max_length=63, db_index=True)),
                ('values', jsonfield.fields.JSONField(blank=True)),
                ('site', models.ForeignKey(related_name='microsite_history', to='sites.Site')),
            ],
            options={
                'verbose_name_plural': 'Microsite histories',
            },
        ),
    ]
