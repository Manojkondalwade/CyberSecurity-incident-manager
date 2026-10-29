"""
database/connection.py
MySQL connection management via SQLAlchemy.
"""
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine connected to MySQL."""
    cfg = st.secrets["mysql"]
    url = URL.create(
        drivername="mysql+pymysql",
        username=cfg["username"],
        password=cfg["password"],
        host=cfg["host"],
        port=int(cfg.get("port", 3306)),
        database=cfg["database"],
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
    )


def get_connection():
    """Context manager: yields a raw SQLAlchemy connection."""
    return get_engine().connect()


def test_connection():
    """Verify the connection; return the current database name."""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT DATABASE()")).scalar_one()


def execute_query(sql: str, params: dict = None):
    """Run a SELECT and return all rows as a list of mappings."""
    with get_engine().connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.mappings().all()


def execute_write(sql: str, params: dict = None):
    """Run an INSERT/UPDATE/DELETE inside a transaction; return lastrowid."""
    with get_engine().begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.lastrowid
