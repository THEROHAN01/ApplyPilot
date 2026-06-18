"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from database import Base
import models  # noqa: F401

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

# RLS policy SQL — applied only when the `app.current_user_id` GUC path is used
# (Supabase-swap target). The API layer enforces tenant isolation in Phase 1.
_RLS_TABLES = ["resumes", "jobs", "applications", "contacts", "email_accounts",
               "follow_ups", "agent_runs", "feedback", "usage_logs"]

# Tables that lack a direct user_id column; RLS is enabled but no owner-policy
# is created here. follow_ups is filtered by application_id; jobs is global
# (no per-user ownership at the DB level in Phase 1).
_NO_USER_ID_TABLES = {"follow_ups", "jobs"}


def upgrade() -> None:
    """Create pgvector extension, all tables, IVFFlat indexes, and RLS scaffold."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(op.get_bind())
    op.execute("CREATE INDEX IF NOT EXISTS ix_resumes_embedding ON resumes "
               "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_jobs_jd_embedding ON jobs "
               "USING ivfflat (jd_embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_applications_user_status "
               "ON applications (user_id, status)")
    # Documented Supabase-swap RLS path (no-op without Supabase auth roles):
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        if table not in _NO_USER_ID_TABLES:
            op.execute(
                f"CREATE POLICY {table}_owner ON {table} USING "
                f"(user_id::text = current_setting('app.current_user_id', true))"
            )


def downgrade() -> None:
    """Drop all tables."""
    Base.metadata.drop_all(op.get_bind())
