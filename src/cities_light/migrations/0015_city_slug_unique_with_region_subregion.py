# Capture unique_with=("region", "subregion") added to AbstractCity.slug.
# This is an application-level change only (autoslug enforces uniqueness in
# Python); no SQL DDL is emitted, but the migration state must match the model.

import autoslug.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cities_light", "0014_fix_search_names_index"),
    ]

    operations = [
        migrations.AlterField(
            model_name="city",
            name="slug",
            field=autoslug.fields.AutoSlugField(
                editable=False,
                populate_from="name_ascii",
                unique_with=("region", "subregion"),
                verbose_name="slug",
            ),
        ),
    ]
