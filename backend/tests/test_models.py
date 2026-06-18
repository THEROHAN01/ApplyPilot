from models import User, Application, ApplicationStatus


def test_user_tablename_and_columns() -> None:
    assert User.__tablename__ == "users"
    assert {"id", "email", "name", "plan", "stripe_customer_id", "created_at"} <= set(
        c.name for c in User.__table__.columns
    )


def test_application_status_enum_values() -> None:
    assert {s.value for s in ApplicationStatus} == {
        "pending", "generated", "sent", "opened", "replied", "rejected", "offer"
    }
    assert Application.__tablename__ == "applications"


def test_application_has_job_relationship() -> None:
    from sqlalchemy import inspect as sa_inspect
    from models import Application
    assert "job" in sa_inspect(Application).relationships
