"""Initial production schema migration

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-08-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Sources Table
    op.create_table(
        "sources",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), default=True),
        sa.Column("fetch_interval_minutes", sa.Integer(), default=60),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 2. Projects Table
    op.create_table(
        "projects",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(50), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("author", sa.String(100), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("raw_skills", sa.JSON(), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("budget_currency", sa.String(10), default="USD"),
        sa.Column("budget_period", sa.String(20), default="project"),
        sa.Column("scope_size", sa.String(20), nullable=True),
        sa.Column("client_name", sa.String(100), nullable=True),
        sa.Column("client_country", sa.String(100), nullable=True),
        sa.Column("score", sa.Float(), default=0.0),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), default="NEW"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()
        ),
    )

    # 3. Opportunities Table
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("win_probability", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("ai_generated_proposal", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # 4. Applications Table
    op.create_table(
        "applications",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(64), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", sa.String(30), default="DISCOVERED"),
        sa.Column("proposed_rate", sa.Float(), nullable=True),
        sa.Column("final_contract_value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("interview_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("opportunities")
    op.drop_table("projects")
    op.drop_table("sources")
