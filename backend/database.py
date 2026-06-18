"""
Module: database.py
Purpose: SQLAlchemy engine, session factory, and declarative Base.
Dependencies: SQLAlchemy 2.0
Author: ApplyPilot
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
