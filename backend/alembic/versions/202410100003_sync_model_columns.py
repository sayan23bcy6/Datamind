"""Sync model columns via idempotent column additions.

Revision ID: 202410100003
Revises: 202410100002
Create Date: 2024-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from app.core.database import Base
# Import models to ensure all tables are registered in Base.metadata
import app.db.models  # noqa: F401

revision = "202410100003"
down_revision = "202410100002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Map of fallback server defaults for non-nullable columns when added to populated tables
    defaults_map = {
        ("human_reviews", "status"): "pending",
        ("human_reviews", "proposal_id"): "",
        ("investigations", "status"): "pending",
        ("investigations", "state"): "PROFILE",
        ("investigations", "max_iterations"): "3",
        ("investigations", "cost_budget"): "200000",
        ("investigations", "cost_used"): "0",
        ("investigations", "iteration"): "0",
        ("watches", "schedule"): "@daily",
        ("watches", "drift_threshold"): "0.10",
        ("watches", "enabled"): "true",
        ("tool_calls", "duration_ms"): "0",
        ("cleaning_decisions", "row_count_delta"): "0",
        ("dataset_versions", "row_count"): "0",
        ("dataset_versions", "column_count"): "0",
        ("dataset_versions", "is_original"): "false",
    }

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue

        live_cols = {col["name"] for col in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name not in live_cols:
                server_default = None
                if col.server_default is not None:
                    server_default = col.server_default
                elif not col.nullable:
                    val = defaults_map.get((table_name, col.name))
                    if val is not None:
                        server_default = val
                    elif isinstance(col.type, (sa.String, sa.Text)):
                        server_default = ""
                    elif isinstance(col.type, (sa.Integer, sa.BigInteger, sa.SmallInteger)):
                        server_default = "0"
                    elif isinstance(col.type, sa.Boolean):
                        server_default = "false"
                    elif isinstance(col.type, sa.DateTime):
                        server_default = sa.func.now()

                new_col = sa.Column(
                    col.name,
                    col.type,
                    nullable=col.nullable,
                    server_default=server_default,
                )
                op.add_column(table_name, new_col)


def downgrade() -> None:
    # Do not drop or rename columns on downgrade to preserve data safety
    pass
