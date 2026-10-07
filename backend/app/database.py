import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import settings

# Resolve database URL: explicit override via settings wins, else default to
# the on-disk SQLite file under backend/database/.
if settings.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
    os.makedirs(DB_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'whis.db')}"

# Guard the most common Postgres URL mistake: `postgresql://...` resolves to
# psycopg2 which we don't ship. Point operators at the correct driver prefix.
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    raise RuntimeError(
        "DATABASE_URL uses the plain 'postgresql://' scheme which resolves "
        "to psycopg2 (not installed). Use 'postgresql+psycopg://...' "
        "instead — WHIS ships psycopg (v3)."
    )

_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # check_same_thread=False lets FastAPI's threadpool hand connections
    # between event-loop tasks. Pool-tuning settings are ignored by SQLite.
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Postgres (or any other server-backed dialect): tune the pool so we
    # don't hold idle connections across the `pool_recycle` window (RDS /
    # pgbouncer default is ~30m) and pre-ping so a recycled-underneath-us
    # connection surfaces at checkout instead of the first query.
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
