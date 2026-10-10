"""Initial schema for datasets and version tracking.

Revision ID: 202410100001
Revises: 
Create Date: 2024-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202410100001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "datasets" not in existing_tables:
        op.create_table(
            "datasets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if "dataset_versions" not in existing_tables:
        op.create_table(
            "dataset_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("dataset_id", sa.String(length=36), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("source_name", sa.String(length=255), nullable=False),
            sa.Column("stored_path", sa.String(length=1024), nullable=False),
            sa.Column("file_size_bytes", sa.Integer(), nullable=True),
            sa.Column("sha256", sa.String(length=128), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False),
            sa.Column("column_count", sa.Integer(), nullable=False),
            sa.Column("is_original", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("parent_version_id", sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
            sa.ForeignKeyConstraint(["parent_version_id"], ["dataset_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("dataset_versions")
    op.drop_table("datasets")
