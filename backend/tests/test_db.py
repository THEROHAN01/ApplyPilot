from sqlalchemy import text
from database import SessionLocal


def test_session_executes_select_one() -> None:
    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1
