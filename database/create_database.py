import os
import logging

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database configuration – reads from .env or falls back to defaults
# ---------------------------------------------------------------------------
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE", "apia")

DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------------------------------------------------------------------------
# SQLAlchemy setup
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class FinancialMetric(Base):
    """Stores extracted financial KPIs per company per year."""

    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)
    revenue = Column(String(255), nullable=True)
    net_income = Column(String(255), nullable=True)
    operating_income = Column(String(255), nullable=True)
    cash_flow = Column(String(255), nullable=True)
    total_assets = Column(String(255), nullable=True)
    total_liabilities = Column(String(255), nullable=True)
    risk_factors = Column(Text, nullable=True)
    growth_drivers = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


    def __repr__(self):
        return f"<FinancialMetric(company='{self.company}', year={self.year})>"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def get_session():
    """Return a new SQLAlchemy session."""
    return SessionLocal()


def create_mysql_database():
    """
    Create the MySQL database if it doesn't exist, then create all tables.

    This connects to MySQL *without* specifying a database first, runs
    CREATE DATABASE IF NOT EXISTS, and then creates the ORM tables.
    """
    server_url = (
        f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
    )
    tmp_engine = create_engine(server_url, echo=False)

    with tmp_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"))
        conn.commit()
        logger.info("Database '%s' ensured.", DB_NAME)

    tmp_engine.dispose()


def create_tables():
    """Create all tables defined by the ORM models."""
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created successfully.")


def init_db():
    """Full initialization: create database + tables."""
    create_mysql_database()
    create_tables()


# ---------------------------------------------------------------------------
# Run standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} ...")
    init_db()
    print(f"Database '{DB_NAME}' and tables are ready.")
