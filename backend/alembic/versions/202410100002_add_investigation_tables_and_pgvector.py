"""Add investigation tables, pgvector extension, and embeddings with HNSW index.

Revision ID: 202410100002
Revises: 202410100001
Create Date: 2024-10-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "202410100002"
down_revision = "202410100001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    if "investigations" not in existing_tables:
        op.create_table(
            "investigations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("dataset_id", sa.String(length=36), nullable=False),
            sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
            sa.Column("output_version_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="PROFILE"),
            sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("cost_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cost_budget", sa.Integer(), nullable=False, server_default="200000"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
            sa.ForeignKeyConstraint(["output_version_id"], ["dataset_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        inv_cols = {col["name"] for col in inspector.get_columns("investigations")}
        if "output_version_id" not in inv_cols:
            op.add_column("investigations", sa.Column("output_version_id", sa.String(length=36), nullable=True))
            op.create_foreign_key("fk_investigations_output_version", "investigations", "dataset_versions", ["output_version_id"], ["id"])
        if "max_iterations" not in inv_cols:
            op.add_column("investigations", sa.Column("max_iterations", sa.Integer(), nullable=False, server_default="3"))

    if "workflow_checkpoints" not in existing_tables:
        op.create_table(
            "workflow_checkpoints",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("state", sa.String(length=32), nullable=False),
            sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "agent_messages" not in existing_tables:
        op.create_table(
            "agent_messages",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "tool_calls" not in existing_tables:
        op.create_table(
            "tool_calls",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
            sa.Column("tool_name", sa.String(length=128), nullable=False),
            sa.Column("input_hash", sa.String(length=128), nullable=False),
            sa.Column("inputs", sa.JSON(), nullable=True),
            sa.Column("outputs", sa.JSON(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "cleaning_decisions" not in existing_tables:
        op.create_table(
            "cleaning_decisions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("dataset_version_id", sa.String(length=36), nullable=False),
            sa.Column("operation", sa.String(length=128), nullable=False),
            sa.Column("target_columns", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("row_count_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("row_indices", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        cd_cols = {col["name"] for col in inspector.get_columns("cleaning_decisions")}
        if "row_indices" not in cd_cols:
            op.add_column("cleaning_decisions", sa.Column("row_indices", sa.JSON(), nullable=True))

    if "evidence" not in existing_tables:
        op.create_table(
            "evidence",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("claim", sa.Text(), nullable=False),
            sa.Column("test_name", sa.String(length=128), nullable=False),
            sa.Column("statistic", sa.String(length=128), nullable=True),
            sa.Column("p_value", sa.String(length=128), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "human_reviews" not in existing_tables:
        op.create_table(
            "human_reviews",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("proposal_id", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("proposal_summary", sa.Text(), nullable=True),
            sa.Column("parameters", sa.JSON(), nullable=True),
            sa.Column("decision", sa.String(length=32), nullable=True),
            sa.Column("reviewer", sa.String(length=128), nullable=True),
            sa.Column("action", sa.String(length=32), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        hr_cols = {col["name"] for col in inspector.get_columns("human_reviews")}
        if "proposal_id" not in hr_cols:
            op.add_column("human_reviews", sa.Column("proposal_id", sa.String(length=128), nullable=False, server_default=""))
        if "proposal_summary" not in hr_cols:
            op.add_column("human_reviews", sa.Column("proposal_summary", sa.Text(), nullable=True))
        if "parameters" not in hr_cols:
            op.add_column("human_reviews", sa.Column("parameters", sa.JSON(), nullable=True))
        if "decision" not in hr_cols:
            op.add_column("human_reviews", sa.Column("decision", sa.String(length=32), nullable=True))

    if "reports" not in existing_tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("investigation_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("path", sa.String(length=512), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "watches" not in existing_tables:
        op.create_table(
            "watches",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("dataset_id", sa.String(length=36), nullable=False),
            sa.Column("schedule", sa.String(length=128), nullable=False, server_default="@daily"),
            sa.Column("drift_threshold", sa.String(length=32), nullable=False, server_default="0.10"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_checked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    if "embeddings" not in existing_tables:
        op.create_table(
            "embeddings",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=64), nullable=False),
            sa.Column("ref_id", sa.String(length=255), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=False),
            sa.Column("vector", Vector(768), nullable=True),
            sa.Column("text_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_embeddings_ref_id", "embeddings", ["ref_id"])
    else:
        emb_cols = {col["name"]: col for col in inspector.get_columns("embeddings")}
        if "ref_id" in emb_cols and getattr(emb_cols["ref_id"]["type"], "length", 0) == 36:
            op.alter_column("embeddings", "ref_id", type_=sa.String(length=255), existing_type=sa.String(length=36))

    if is_postgres:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_hnsw ON embeddings USING hnsw (vector vector_cosine_ops);"
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_hnsw;")

    op.drop_table("embeddings")
    op.drop_table("watches")
    op.drop_table("reports")
    op.drop_table("human_reviews")
    op.drop_table("evidence")
    op.drop_table("cleaning_decisions")
    op.drop_table("tool_calls")
    op.drop_table("agent_messages")
    op.drop_table("workflow_checkpoints")
    op.drop_table("investigations")
