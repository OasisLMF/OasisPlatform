# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-11-29 14:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0002_relatedfile_filename'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relatedfile',
            name='filename',
            field=models.CharField(blank=True, default=None, editable=False, max_length=255),
        ),
    ]
