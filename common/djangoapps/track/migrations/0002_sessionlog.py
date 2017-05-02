# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('track', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('dtcreated', models.DateTimeField(auto_now_add=True, verbose_name=b'creation date')),
                ('username', models.CharField(max_length=32, blank=True)),
                ('courseid', models.TextField(blank=True)),
                ('start_time', models.DateTimeField(verbose_name=b'started at')),
                ('end_time', models.DateTimeField(verbose_name=b'ended at')),
                ('host', models.CharField(max_length=64, blank=True)),
            ],
        ),
    ]
