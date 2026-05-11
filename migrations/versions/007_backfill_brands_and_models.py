"""backfill_brands_and_models

Data migration: creates Brand and AssetModel rows from the existing
legacy `brand` and `model` text columns on asset and peripheral, then
populates the new brand_id / model_id FKs.

Assumes data is already normalized upstream — no fuzzy matching, no
alias table. Exact string match (after TRIM) only.

Revision ID: 007
Revises: 006
Create Date: 2026-04-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # --- 1. Collect distinct brand names from asset + peripheral ---
    brand_rows = bind.execute(sa.text("""
        SELECT DISTINCT TRIM(brand) AS name
        FROM (
            SELECT brand FROM asset WHERE brand IS NOT NULL AND TRIM(brand) <> ''
            UNION
            SELECT brand FROM peripheral WHERE brand IS NOT NULL AND TRIM(brand) <> ''
        ) AS b
    """)).fetchall()

    brand_name_to_id = {}
    for row in brand_rows:
        name = row[0]
        if not name:
            continue
        # Insert if not already present; rely on unique constraint.
        existing = bind.execute(
            sa.text("SELECT id FROM brand WHERE name = :n"), {"n": name}
        ).fetchone()
        if existing:
            brand_name_to_id[name] = existing[0]
            continue
        result = bind.execute(
            sa.text("""
                INSERT INTO brand (name, created_at)
                VALUES (:n, CURRENT_TIMESTAMP)
            """),
            {"n": name},
        )
        # Fetch the id back in a portable way.
        new_id = bind.execute(
            sa.text("SELECT id FROM brand WHERE name = :n"), {"n": name}
        ).fetchone()[0]
        brand_name_to_id[name] = new_id

    # --- 2. Collect distinct (brand, model) pairs from asset only ---
    # Peripheral did not have a legacy `model` text column.
    model_rows = bind.execute(sa.text("""
        SELECT DISTINCT TRIM(brand) AS brand_name, TRIM(model) AS model_name
        FROM asset
        WHERE model IS NOT NULL AND TRIM(model) <> ''
          AND brand IS NOT NULL AND TRIM(brand) <> ''
    """)).fetchall()

    model_key_to_id = {}  # (brand_name, model_name) -> asset_model.id
    for row in model_rows:
        brand_name, model_name = row[0], row[1]
        if not brand_name or not model_name:
            continue
        brand_id = brand_name_to_id.get(brand_name)
        if brand_id is None:
            continue
        existing = bind.execute(
            sa.text("SELECT id FROM asset_model WHERE brand_id = :b AND name = :n"),
            {"b": brand_id, "n": model_name},
        ).fetchone()
        if existing:
            model_key_to_id[(brand_name, model_name)] = existing[0]
            continue
        bind.execute(
            sa.text("""
                INSERT INTO asset_model (name, brand_id, created_at)
                VALUES (:n, :b, CURRENT_TIMESTAMP)
            """),
            {"n": model_name, "b": brand_id},
        )
        new_id = bind.execute(
            sa.text("SELECT id FROM asset_model WHERE brand_id = :b AND name = :n"),
            {"b": brand_id, "n": model_name},
        ).fetchone()[0]
        model_key_to_id[(brand_name, model_name)] = new_id

    # --- 3. Populate asset.brand_id and asset.model_id ---
    bind.execute(sa.text("""
        UPDATE asset
        SET brand_id = (
            SELECT b.id FROM brand b WHERE b.name = TRIM(asset.brand)
        )
        WHERE brand IS NOT NULL AND TRIM(brand) <> ''
    """))
    bind.execute(sa.text("""
        UPDATE asset
        SET model_id = (
            SELECT m.id FROM asset_model m
            WHERE m.name = TRIM(asset.model)
              AND m.brand_id = asset.brand_id
        )
        WHERE model IS NOT NULL AND TRIM(model) <> ''
          AND brand_id IS NOT NULL
    """))

    # --- 4. Populate peripheral.brand_id (no model column on peripheral) ---
    bind.execute(sa.text("""
        UPDATE peripheral
        SET brand_id = (
            SELECT b.id FROM brand b WHERE b.name = TRIM(peripheral.brand)
        )
        WHERE brand IS NOT NULL AND TRIM(brand) <> ''
    """))


def downgrade():
    # Clear FKs; brand/model text columns are still present so data is not lost.
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE asset SET brand_id = NULL, model_id = NULL"))
    bind.execute(sa.text("UPDATE peripheral SET brand_id = NULL, model_id = NULL"))
    bind.execute(sa.text("DELETE FROM asset_model"))
    bind.execute(sa.text("DELETE FROM brand"))
