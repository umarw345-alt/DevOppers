from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def create_session_factory(database_url: str):
    # Hosted Postgres (e.g. Neon) hands out postgres:// URLs; SQLAlchemy needs the psycopg driver named.
    database_url = database_url.replace("postgres://", "postgresql://", 1).replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(database_url, pool_pre_ping=True)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)
