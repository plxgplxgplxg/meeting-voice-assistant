"""timezone aware timestamps

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17 10:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW_DEFAULT_COLUMNS = ("created_at", "updated_at", "usage_at", "added_at", "current_period_start")

FIND_NAIVE_COLUMNS = """
SELECT table_name, column_name, column_default
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND data_type = 'timestamp without time zone'
  AND table_name <> 'alembic_version'
"""


def upgrade() -> None:
    """Convert every naive timestamp (stored as UTC) to timestamptz and add now() defaults."""
    connection = op.get_bind()
    rows = connection.exec_driver_sql(FIND_NAIVE_COLUMNS).fetchall()
    for table, column, default in rows:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f"TYPE timestamptz USING \"{column}\" AT TIME ZONE 'UTC'"
        )
        if column in NOW_DEFAULT_COLUMNS and default is None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT now()')


def downgrade() -> None:
    """Convert timestamptz columns back to naive UTC timestamps."""
    connection = op.get_bind()
    rows = connection.exec_driver_sql(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND data_type = 'timestamp with time zone'
        """
    ).fetchall()
    for table, column in rows:
        if column in NOW_DEFAULT_COLUMNS:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f"TYPE timestamp USING \"{column}\" AT TIME ZONE 'UTC'"
        )
