"""Django JSON Serializer override."""

from django.core.serializers import json as upstream

from .base import BaseSerializerMixin


__all__ = ('Serializer', 'Deserializer')


class Serializer(BaseSerializerMixin, upstream.Serializer):
    """Sorted dict JSON serializer."""


Deserializer = upstream.Deserializer
