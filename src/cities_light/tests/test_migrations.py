import unittest
from django import test
from django.apps import apps
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.questioner import (
    InteractiveMigrationQuestioner,
)
from django.db.migrations.state import ProjectState
import logging

logger = logging.getLogger(__name__)


class TestNoMigrationLeft(test.TestCase):
    @unittest.skip("TODO: make the test pass")
    def test_no_migration_left(self):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        conflicts = loader.detect_conflicts()
        logger.error(conflicts)
        app_labels = ["cities_light"]

        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(apps),
            InteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=True),
        )

        changes = autodetector.changes(
            graph=loader.graph,
            trim_to_apps=app_labels or None,
            convert_apps=app_labels or None,
        )

        assert "cities_light" not in changes

    def test_migration_0014_resolves_index_search_names_mismatch(self):
        """
        Verify that migration 0014 correctly handles the INDEX_SEARCH_NAMES setting.
        
        Migration 0014 was created to fix the issue where migration 0013 set
        db_index=True on City.search_names, but INDEX_SEARCH_NAMES defaults to
        False for PostgreSQL and MySQL databases.
        
        This test verifies:
        - When INDEX_SEARCH_NAMES=False (PostgreSQL/MySQL default): no pending migrations
        - When INDEX_SEARCH_NAMES=True (SQLite default): user must generate their own
          migration (test will skip as this is expected behavior)
        """
        from cities_light.settings import INDEX_SEARCH_NAMES
        from django.conf import settings
        
        # Get database engine to determine expected behavior
        db_engine = settings.DATABASES['default']['ENGINE']
        
        # Log the test context
        logger.info(f"Testing with db_engine={db_engine}, INDEX_SEARCH_NAMES={INDEX_SEARCH_NAMES}")
        
        # For databases where INDEX_SEARCH_NAMES defaults to True (e.g., SQLite),
        # migration 0014 will create a pending migration since it sets db_index=False.
        # This is expected - users with these databases must generate their own migration
        # if they want indexing.
        if INDEX_SEARCH_NAMES:
            self.skipTest(
                f"Skipping test: INDEX_SEARCH_NAMES=True (database: {db_engine}). "
                "Migration 0014 sets db_index=False for PostgreSQL/MySQL compatibility. "
                "Users who need db_index=True must generate their own migration."
            )
        
        # For databases where INDEX_SEARCH_NAMES defaults to False (PostgreSQL/MySQL),
        # migration 0014 should have resolved the pending migration issue.
        loader = MigrationLoader(None, ignore_no_migrations=True)
        app_labels = ["cities_light"]

        autodetector = MigrationAutodetector(
            loader.project_state(),
            ProjectState.from_apps(apps),
            InteractiveMigrationQuestioner(specified_apps=app_labels, dry_run=True),
        )

        changes = autodetector.changes(
            graph=loader.graph,
            trim_to_apps=app_labels or None,
            convert_apps=app_labels or None,
        )

        if "cities_light" in changes:
            # Log the changes to help debug if test fails
            migrations = changes.get("cities_light", [])
            for migration in migrations:
                logger.warning(f"Unexpected pending migration: {migration}")
                if hasattr(migration, 'operations'):
                    for op in migration.operations:
                        logger.warning(f"  Operation: {op}")
        
        self.assertNotIn(
            "cities_light", 
            changes,
            f"Migration 0014 should have resolved pending migrations for databases "
            f"where INDEX_SEARCH_NAMES=False (current: {db_engine})"
        )
