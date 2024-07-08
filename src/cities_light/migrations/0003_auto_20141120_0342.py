from django.db import migrations
from cities_light.abstract_models import ToSearchTextField

from cities_light.settings import INDEX_SEARCH_NAMES


class Migration(migrations.Migration):

    dependencies = [
        ('cities_light', '0002_city'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='search_names',
            field=ToSearchTextField(default=b'', max_length=4000, db_index=INDEX_SEARCH_NAMES, blank=True),
            preserve_default=True,
        ),
    ]
