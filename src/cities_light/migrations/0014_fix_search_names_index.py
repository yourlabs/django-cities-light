# Fix migration 0013 which hardcoded db_index=True, breaking MySQL/PostgreSQL
# where INDEX_SEARCH_NAMES is False by default (btree index unsupported on TEXT).

import cities_light.abstract_models
from cities_light.settings import INDEX_SEARCH_NAMES
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "cities_light",
            "0013_alter_city_alternate_names_alter_city_country_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="city",
            name="search_names",
            field=cities_light.abstract_models.ToSearchTextField(
                blank=True,
                db_index=INDEX_SEARCH_NAMES,
                default="",
                max_length=4000,
                verbose_name="search names",
            ),
        ),
    ]
