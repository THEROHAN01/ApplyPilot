"""
Module: tests/test_migration.py
Purpose: Verify that all expected tables are created by the conftest schema fixture.
Author: ApplyPilot
"""
from sqlalchemy import inspect
from tests.conftest import engine


def test_all_tables_created() -> None:
    """Assert all 10 domain tables exist after the autouse _schema fixture runs."""
    names = set(inspect(engine).get_table_names())
    assert {"users", "resumes", "jobs", "applications", "contacts",
            "email_accounts", "follow_ups", "agent_runs", "feedback",
            "usage_logs"} <= names
