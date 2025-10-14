"""Database models for the ticket price scraper."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, Session

Base = declarative_base()


class Alert(Base):
    """Alert model for tracking ticket price thresholds."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)  # ticketmaster, stubhub, viagogo
    source_url = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    last_notified_price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    price_records = relationship(
        "PriceRecord", back_populates="alert", cascade="all, delete-orphan"
    )
    notification_logs = relationship(
        "NotificationLog", back_populates="alert", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, name='{self.name}', source='{self.source}', target_price={self.target_price})>"


class PriceRecord(Base):
    """Historical price data for alerts."""

    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    price = Column(Float, nullable=False)
    availability = Column(String, nullable=True)  # available, sold_out, limited, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON, nullable=True)  # Store raw scraping data for debugging

    # Relationships
    alert = relationship("Alert", back_populates="price_records")

    def __repr__(self):
        return f"<PriceRecord(id={self.id}, alert_id={self.alert_id}, price={self.price}, timestamp={self.timestamp})>"


class NotificationLog(Base):
    """Log of sent notifications."""

    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    trigger_reason = Column(String, nullable=False)  # first_time, price_drop
    price = Column(Float, nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="notification_logs")

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, alert_id={self.alert_id}, trigger_reason='{self.trigger_reason}', price={self.price})>"


def init_db(db_path: str = "sqlite:///data/tickets.db") -> Session:
    """Initialize the database and return a session.

    Args:
        db_path: SQLite database path (default: sqlite:///data/tickets.db)

    Returns:
        SQLAlchemy Session object
    """
    engine = create_engine(
        db_path,
        connect_args={"check_same_thread": False} if "sqlite" in db_path else {},
    )
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def get_session(db_path: str = "sqlite:///data/tickets.db") -> Session:
    """Get a database session.

    Args:
        db_path: SQLite database path (default: sqlite:///data/tickets.db)

    Returns:
        SQLAlchemy Session object
    """
    engine = create_engine(
        db_path,
        connect_args={"check_same_thread": False} if "sqlite" in db_path else {},
    )
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()
