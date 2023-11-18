"""Shared code for serializers."""

import collections
import datetime
import decimal


class BaseSerializerMixin(object):
    """Serializer mixin for predictible and cross-db dumps."""

    @classmethod
    def recursive_dict_sort(cls, data):
        """
        Return a recursive OrderedDict for a dict.

        Django's default model-to-dict logic - implemented in
        django.core.serializers.python.Serializer.get_dump_object() - returns a
        dict, this app registers a slightly modified version of the default
        json serializer which returns OrderedDicts instead.
        """
        ordered_data = collections.OrderedDict(sorted(data.items()))

        for key, value in ordered_data.items():
            if isinstance(value, dict):
                ordered_data[key] = cls.recursive_dict_sort(value)

        return ordered_data

    @classmethod
    def remove_microseconds(cls, data):
        """
        Strip microseconds from datetimes for mysql.

        MySQL doesn't have microseconds in datetimes, so dbdiff's serializer
        removes microseconds from datetimes so that fixtures are cross-database
        compatible which make them usable for cross-database testing.
        """
        for key, value in data['fields'].items():
            if not isinstance(value, datetime.datetime):
                continue

            data['fields'][key] = datetime.datetime(
                year=value.year,
                month=value.month,
                day=value.day,
                hour=value.hour,
                minute=value.minute,
                second=value.second,
                tzinfo=value.tzinfo
            )

    @classmethod
    def normalize_decimals(cls, data):
        """
        Strip trailing zeros for constitency.

        In addition, dbdiff serialization forces Decimal normalization, because
        trailing zeros could happen in inconsistent ways.
        """
        for key, value in data['fields'].items():
            if not isinstance(value, decimal.Decimal):
                continue

            if value % 1 == 0:
                data['fields'][key] = int(value)
            else:
                data['fields'][key] = value.normalize()

    def get_dump_object(self, obj):
        """
        Actual method used by Django serializers to dump dicts.

        By overridding this method, we're able to run our various
        data dump predictability methods.
        """
        data = super(BaseSerializerMixin, self).get_dump_object(obj)
        self.remove_microseconds(data)
        self.normalize_decimals(data)
        data = self.recursive_dict_sort(data)
        return data
