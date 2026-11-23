from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def normalize_database_url(database_url: str) -> str:
    """Hosted Postgres (e.g. Neon) hands out postgres:// URLs; SQLAlchemy needs the psycopg driver named."""
    return database_url.replace("postgres://", "postgresql://", 1).replace("postgresql://", "postgresql+psycopg://", 1)


def create_session_factory(database_url: str):
    engine = create_engine(normalize_database_url(database_url), pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
