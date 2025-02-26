# Generated by Django 5.1.6 on 2025-02-26 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cities_light', '0011_alter_city_country_alter_city_region_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='translations',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='translations',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='region',
            name='translations',
            field=models.JSONField(default=dict, blank=True),
        ),
        migrations.AddField(
            model_name='subregion',
            name='translations',
            field=models.JSONField(default=dict, blank=True),
        ),
    ]
