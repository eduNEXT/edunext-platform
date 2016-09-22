# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Redirection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain', models.CharField(help_text=b'use only the domain name, e.g. cursos.edunext.co', max_length=253, db_index=True)),
                ('target', models.CharField(max_length=253)),
                ('scheme', models.CharField(default=b'http', max_length=5, choices=[(b'http', b'http'), (b'https', b'https')])),
                ('status', models.IntegerField(default=301, choices=[(301, b'Temporary'), (302, b'Permanent')])),
            ],
        ),
    ]
