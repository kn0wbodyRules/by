"""seed rate table and model versions

Revision ID: 46fb3c13e2dc
Revises: 422f7c6e383f
Create Date: 2026-07-17 12:14:57.297112

"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '46fb3c13e2dc'
down_revision: Union[str, Sequence[str], None] = '422f7c6e383f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_FILE = Path(__file__).resolve().parents[2] / "app" / "seed_data" / "rate_table_seed.json"


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    # Reflect against sa.table(), not the ORM model — insulates this migration from
    # future model changes (Alembic best practice).
    # create_type=False: the ENUM types already exist from the prior migration —
    # this reflection must not try to CREATE TYPE again.
    material_unit_type = postgresql.ENUM(
        "sqft", "kg", "bag", "unit", "tonne", "cft", name="material_unit", create_type=False
    )
    model_version_status_type = postgresql.ENUM(
        "active", "training", "retired", name="model_version_status", create_type=False
    )

    rate_table = sa.table(
        "rate_table",
        sa.column("id", sa.String),
        sa.column("material_name", sa.String),
        sa.column("unit", material_unit_type),
        sa.column("rate_per_unit", sa.Float),
        sa.column("location", sa.String),
        sa.column("source_label", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    model_versions = sa.table(
        "model_versions",
        sa.column("id", sa.String),
        sa.column("model_version", sa.String),
        sa.column("trained_on_date", sa.Date),
        sa.column("validation_score", sa.Float),
        sa.column("status", model_version_status_type),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    seed_rows = json.loads(SEED_FILE.read_text())
    op.bulk_insert(
        rate_table,
        [
            {
                "id": str(uuid.uuid4()),
                "material_name": row["material_name"],
                "unit": row["unit"],
                "rate_per_unit": row["rate_per_unit"],
                "location": row["location"],
                "source_label": row["source_label"],
                "created_at": now,
                "updated_at": now,
            }
            for row in seed_rows
        ],
    )

    op.bulk_insert(
        model_versions,
        [
            {
                "id": str(uuid.uuid4()),
                "model_version": "fallback-constant-1.0",
                "trained_on_date": None,
                "validation_score": None,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM rate_table WHERE source_label LIKE 'PLACEHOLDER%'")
    op.execute("DELETE FROM model_versions WHERE model_version = 'fallback-constant-1.0'")
