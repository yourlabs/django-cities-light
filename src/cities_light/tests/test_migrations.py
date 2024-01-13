import unittest
from io import StringIO

from django import test
from django.core.management import call_command
from django.test.utils import override_settings


@override_settings(
    MIGRATION_MODULES={
        "cities_light": "cities_light.migrations",
    },
)
class TestNoMigrationLeft(test.TestCase):
    def test_no_migration_left(self):
        out = StringIO()
        try:
            call_command(
                "makemigrations",
                "cities_light",
                "--dry-run",
                "--check",
                stdout=out,
                stderr=StringIO(),
            )
        except SystemExit:  # pragma: no cover
            raise AssertionError("Pending migrations:\n" + out.getvalue()) from None
