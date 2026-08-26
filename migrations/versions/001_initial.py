"""Initial schema matching KnowledgeOps models.

Revision ID: 001
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stable_id", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("classification", sa.String(length=64), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("allowed_groups", sa.JSON(), nullable=True),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_stable_id", "documents", ["stable_id"], unique=True)

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("previous_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_content_hash", "document_versions", ["content_hash"])

    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=512), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_strategy", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=256), nullable=True),
        sa.Column("embedding_model_version", sa.String(length=64), nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])
    op.create_index("ix_chunks_qdrant_point_id", "chunks", ["qdrant_point_id"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("index_version_id", sa.String(length=36), nullable=True),
        sa.Column("documents_discovered", sa.Integer(), nullable=False),
        sa.Column("documents_new", sa.Integer(), nullable=False),
        sa.Column("documents_modified", sa.Integer(), nullable=False),
        sa.Column("documents_unchanged", sa.Integer(), nullable=False),
        sa.Column("documents_deleted", sa.Integer(), nullable=False),
        sa.Column("documents_failed", sa.Integer(), nullable=False),
        sa.Column("chunks_indexed", sa.Integer(), nullable=False),
        sa.Column("chunks_removed", sa.Integer(), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingestion_steps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("step_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_steps_ingestion_run_id", "ingestion_steps", ["ingestion_run_id"])

    op.create_table(
        "ingestion_errors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("error_type", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_errors_ingestion_run_id", "ingestion_errors", ["ingestion_run_id"]
    )

    op.create_table(
        "index_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("embedding_config", sa.JSON(), nullable=True),
        sa.Column("chunk_config", sa.JSON(), nullable=True),
        sa.Column("retrieval_config", sa.JSON(), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("evaluation_results", sa.JSON(), nullable=True),
        sa.Column("promotion_status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_index_versions_name", "index_versions", ["name"], unique=True)

    op.create_table(
        "queries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("user_group", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("index_version_id", sa.String(length=36), nullable=True),
        sa.Column("retrieval_latency_ms", sa.Integer(), nullable=True),
        sa.Column("generation_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "query_retrievals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("dense_score", sa.Float(), nullable=True),
        sa.Column("sparse_score", sa.Float(), nullable=True),
        sa.Column("fusion_score", sa.Float(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("used_in_context", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_retrievals_query_id", "query_retrievals", ["query_id"])
    op.create_index("ix_query_retrievals_chunk_id", "query_retrievals", ["chunk_id"])

    op.create_table(
        "answers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("query_id", sa.String(length=36), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("confidence_level", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("knowledge_gap", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["query_id"], ["queries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_id"),
    )

    op.create_table(
        "citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("answer_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_title", sa.String(length=512), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=512), nullable=True),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(["answer_id"], ["answers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_answer_id", "citations", ["answer_id"])

    op.create_table(
        "knowledge_gaps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("normalized_question", sa.Text(), nullable=True),
        sa.Column("cluster_id", sa.String(length=36), nullable=True),
        sa.Column("suggested_topic", sa.String(length=512), nullable=True),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("best_retrieval_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_gaps_cluster_id", "knowledge_gaps", ["cluster_id"])

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("dataset_name", sa.String(length=256), nullable=False),
        sa.Column("index_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_document", sa.String(length=512), nullable=True),
        sa.Column("retrieved_documents", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_run_id"], ["evaluation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_results_evaluation_run_id", "evaluation_results", ["evaluation_run_id"]
    )

    op.create_table(
        "provider_usage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=256), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("provider_usage")
    op.drop_index("ix_evaluation_results_evaluation_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_index("ix_knowledge_gaps_cluster_id", table_name="knowledge_gaps")
    op.drop_table("knowledge_gaps")
    op.drop_index("ix_citations_answer_id", table_name="citations")
    op.drop_table("citations")
    op.drop_table("answers")
    op.drop_index("ix_query_retrievals_chunk_id", table_name="query_retrievals")
    op.drop_index("ix_query_retrievals_query_id", table_name="query_retrievals")
    op.drop_table("query_retrievals")
    op.drop_table("queries")
    op.drop_index("ix_index_versions_name", table_name="index_versions")
    op.drop_table("index_versions")
    op.drop_index("ix_ingestion_errors_ingestion_run_id", table_name="ingestion_errors")
    op.drop_table("ingestion_errors")
    op.drop_index("ix_ingestion_steps_ingestion_run_id", table_name="ingestion_steps")
    op.drop_table("ingestion_steps")
    op.drop_table("ingestion_runs")
    op.drop_index("ix_chunks_qdrant_point_id", table_name="chunks")
    op.drop_index("ix_chunks_content_hash", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_document_versions_content_hash", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")
    op.drop_index("ix_documents_stable_id", table_name="documents")
    op.drop_table("documents")
