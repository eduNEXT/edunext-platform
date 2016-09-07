# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('microsite_configuration', '0002_auto_20160202_0228'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='microsite',
            name='site',
        ),
        migrations.AddField(
            model_name='microsite',
            name='subdomain',
            field=models.CharField(default='localhost', max_length=127, db_index=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='microsite',
            name='key',
            field=models.CharField(max_length=63, db_index=True),
        ),
    ]
