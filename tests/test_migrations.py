"""
Database migration integration tests.

These tests verify that Alembic migrations apply cleanly against a real
PostgreSQL database. They require DATABASE_URL to point to a Postgres
instance (the CI workflow provides one automatically).

Skipped when DATABASE_URL is not set or points to SQLite.
"""
import os
import pytest
from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.environ.get('DATABASE_URL', '')
requires_postgres = pytest.mark.skipif(
    'postgresql' not in DATABASE_URL,
    reason='Requires PostgreSQL (set DATABASE_URL)'
)


def _make_app():
    """Create a Flask app configured for migration testing."""
    from src import create_app, limiter
    app = create_app(test_config={
        'SQLALCHEMY_DATABASE_URI': DATABASE_URL,
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test',
        'RATELIMIT_ENABLED': False,
    })
    limiter.enabled = False
    return app


def _clean_db(engine):
    """Drop all tables so migrations start from scratch."""
    with engine.connect() as conn:
        conn.execute(text('DROP SCHEMA public CASCADE'))
        conn.execute(text('CREATE SCHEMA public'))
        conn.commit()


@requires_postgres
class TestMigrations:

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create app, engine, and clean DB before each test."""
        self.app = _make_app()
        self.engine = create_engine(DATABASE_URL)
        _clean_db(self.engine)
        yield
        _clean_db(self.engine)
        self.engine.dispose()

    def _upgrade(self, revision='head'):
        with self.app.app_context():
            from flask_migrate import upgrade
            upgrade(revision=revision)

    def _downgrade(self, revision='base'):
        with self.app.app_context():
            from flask_migrate import downgrade
            downgrade(revision=revision)

    def test_upgrade_head(self):
        """Migrations apply cleanly from empty DB to head."""
        self._upgrade()

        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        # Sanity check: core tables exist
        assert 'user' in tables
        assert 'asset' in tables
        assert 'alembic_version' in tables

        # Verify alembic_version is set
        with self.engine.connect() as conn:
            result = conn.execute(text('SELECT version_num FROM alembic_version')).fetchone()
            assert result is not None
            assert result[0] == '001'

    def test_downgrade_base(self):
        """Migrations can be fully rolled back."""
        self._upgrade()
        self._downgrade()

        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        # Only alembic_version should remain (Alembic doesn't drop it)
        user_tables = [t for t in tables if t != 'alembic_version']
        assert len(user_tables) == 0, f"Tables left after downgrade: {user_tables}"

    def test_upgrade_is_idempotent(self):
        """Running upgrade twice doesn't fail."""
        self._upgrade()
        self._upgrade()

        inspector = inspect(self.engine)
        assert 'user' in inspector.get_table_names()

    def test_models_match_migrations(self):
        """
        After applying migrations, the DB schema should match the models.
        If autogenerate detects differences, models and migrations are out of sync.
        """
        self._upgrade()

        with self.app.app_context():
            from src.extensions import db
            from alembic.autogenerate import compare_metadata
            from alembic.migration import MigrationContext

            with self.engine.connect() as conn:
                migration_ctx = MigrationContext.configure(conn)
                diff = compare_metadata(migration_ctx, db.metadata)

            # Ignore 'remove_table' diffs — these are tables from optional
            # plugins (e.g. opsdeck-enterprise) that exist in migrations
            # but whose models aren't installed in this environment.
            meaningful = [d for d in diff if d[0] != 'remove_table']

            if meaningful:
                changes = "\n".join(f"  - {d}" for d in meaningful)
                pytest.fail(
                    f"Models and migrations are out of sync.\n"
                    f"Detected {len(meaningful)} difference(s):\n{changes}"
                )
