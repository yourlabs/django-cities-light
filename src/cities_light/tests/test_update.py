"""Tests for update records."""
import unittest

from .base import TestImportBase, FixtureDir


class TestUpdate(TestImportBase):
    """Tests update procedure."""

    def test_update_fields(self):
        """Test all fields are updated."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'update_country',
            'update_region',
            'update_subregion',
            'update_city',
            'update_translations',
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('update_fields.json')
        )

    def test_update_fields_wrong_timezone(self):
        """Test all fields are updated, but timezone field is wrong."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'update_country',
            'update_region',
            'update_subregion',
            'update_city_wtz',
            'update_translations',
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('update_fields_wtz.json')
        )

    def test_change_country(self):
        """Test change country for region/city."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'change_country',
            'update_region',
            'update_subregion',
            'update_city',
            'update_translations',
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('change_country.json')
        )

    def test_change_region_and_country(self):
        """Test change region and country."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'change_country',
            'change_region',
            'update_subregion',
            'update_city',
            'update_translations',
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('change_region_and_country.json')
        )

    def test_keep_slugs(self):
        """Test --keep-slugs option."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'update_country',
            'update_region',
            'update_subregion',
            'update_city',
            'update_translations',
            keep_slugs=True
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('keep_slugs.json'),
        )

    def test_add_records(self):
        """Test that new records are added."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'add_country',
            'add_region',
            'add_subregion',
            'add_city',
            'add_translations'
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('add_records.json')
        )

    def test_noinsert(self):
        """Test --noinsert option."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'initial_country',
            'initial_region',
            'initial_subregion',
            'initial_city',
            'initial_translations'
        )

        self.import_data(
            fixture_dir,
            'add_country',
            'add_region',
            'add_subregion',
            'add_city',
            'add_translations',
            noinsert=True
        )

        self.assertNoDiff(
            fixture_dir.get_file_path('noinsert.json'),
        )

    # TODO: make the test pass
    @unittest.skip("Obsolete records are not removed yet.")
    def test_remove_records(self):
        """Test that obsolete records are removed."""
        fixture_dir = FixtureDir('update')

        self.import_data(
            fixture_dir,
            'remove_initial_country',
            'remove_initial_region',
            'remove_initial_subregion',
            'remove_initial_city',
            'remove_initial_translations'
        )

        self.import_data(
            fixture_dir,
            'remove_country',
            'remove_region',
            'remove_subregion',
            'remove_city',
            'remove_translations'
        )

        Fixture(
            fixture_dir.get_file_path('remove_records.json')
        ).assertNoDiff()
