# Database Versioning

OpsDeck uses **Flask-Migrate** (Alembic) for database schema versioning. Migrations are numbered sequentially (`001_initial.py`, `002_add_notes_field.py`, etc.) and auto-generated from SQLAlchemy model changes.

## How It Works

The migration system is configured with two key customizations:

- **`migrations/alembic.ini`**: `file_template = %%(rev)s_%%(slug)s` uses the revision ID as filename prefix.
- **`migrations/env.py`**: `process_revision_directives` scans `migrations/versions/` for the highest `NNN_` prefix and assigns `NNN+1` as the revision ID.

This means filenames are automatically numbered — no manual naming needed.

## Creating a New Migration

When you modify a SQLAlchemy model (add a column, create a table, change a constraint, etc.):

```bash
# With Docker
docker compose run --rm web flask db migrate -m "add_notes_to_supplier"

# Without Docker (local venv)
flask db migrate -m "add_notes_to_supplier"
```

This will generate a file like `migrations/versions/002_add_notes_to_supplier.py`.

**Always review the generated file** before applying it. Alembic's autogenerate is good but not perfect — it may miss some changes (e.g., renamed columns look like a drop + add).

## Applying Migrations

```bash
# Apply all pending migrations
flask db upgrade

# Apply up to a specific revision
flask db upgrade 002
```

## Rolling Back

```bash
# Revert the last migration
flask db downgrade -1

# Revert to a specific revision
flask db downgrade 001
```

## Checking Current State

```bash
# Show current revision
flask db current

# Show migration history
flask db history
```

## Guidelines

- **One migration per change**: don't bundle unrelated schema changes.
- **Use descriptive `-m` messages**: they become the filename slug (e.g., `add_website_to_supplier`, `make_supplier_nullable`).
- **Never edit an applied migration**: if it's already been run in any environment, create a new migration to fix it.
- **Review `upgrade()` and `downgrade()`**: make sure `downgrade()` properly reverses the changes.
- **Avoid data migrations in schema files**: if you need to backfill data, do it in a separate migration or script.
