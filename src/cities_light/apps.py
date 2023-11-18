from django.apps import AppConfig
from django.core.serializers import register_serializer


class CitiesLightConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'cities_light'

    def ready(self):
        register_serializer('sorted_json', 'cities_light.serializers.json')
