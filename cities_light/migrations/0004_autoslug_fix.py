# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-13 15:30
from __future__ import unicode_literals

import autoslug.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cities_light', '0003_auto_20141120_0342'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=b'name_ascii'),
        ),
        migrations.AlterField(
            model_name='country',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=b'name_ascii'),
        ),
        migrations.AlterField(
            model_name='region',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=b'name_ascii'),
        ),
    ]
