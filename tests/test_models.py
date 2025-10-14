"""Tests for database models."""
import pytest
from datetime import datetime

from src.models import Alert, PriceRecord, NotificationLog


class TestAlert:
    """Tests for Alert model."""

    def test_create_alert(self, db_session):
        """Test creating an alert."""
        alert = Alert(
            name="Test Event",
            source="ticketmaster",
            source_url="https://www.ticketmaster.com/test",
            target_price=100.00,
        )
        db_session.add(alert)
        db_session.commit()

        assert alert.id is not None
        assert alert.name == "Test Event"
        assert alert.source == "ticketmaster"
        assert alert.target_price == 100.00
        assert alert.is_active is True
        assert alert.last_notified_price is None

    def test_alert_relationships(self, db_session, sample_alert):
        """Test alert relationships with price records and notifications."""
        # Add price records
        price1 = PriceRecord(
            alert_id=sample_alert.id, price=120.00, availability="available"
        )
        price2 = PriceRecord(
            alert_id=sample_alert.id, price=110.00, availability="available"
        )
        db_session.add_all([price1, price2])

        # Add notification log
        notification = NotificationLog(
            alert_id=sample_alert.id,
            trigger_reason="first_time",
            price=95.00,
        )
        db_session.add(notification)
        db_session.commit()

        # Test relationships
        assert len(sample_alert.price_records) == 2
        assert len(sample_alert.notification_logs) == 1
        assert sample_alert.price_records[0].price == 120.00
        assert sample_alert.notification_logs[0].trigger_reason == "first_time"

    def test_alert_repr(self, sample_alert):
        """Test alert string representation."""
        repr_str = repr(sample_alert)
        assert "Alert" in repr_str
        assert sample_alert.name in repr_str
        assert str(sample_alert.target_price) in repr_str


class TestPriceRecord:
    """Tests for PriceRecord model."""

    def test_create_price_record(self, db_session, sample_alert):
        """Test creating a price record."""
        record = PriceRecord(
            alert_id=sample_alert.id,
            price=89.99,
            availability="available",
            raw_data={"test": "data"},
        )
        db_session.add(record)
        db_session.commit()

        assert record.id is not None
        assert record.alert_id == sample_alert.id
        assert record.price == 89.99
        assert record.availability == "available"
        assert record.raw_data == {"test": "data"}
        assert isinstance(record.timestamp, datetime)

    def test_price_record_relationship(self, db_session, sample_alert):
        """Test price record relationship back to alert."""
        record = PriceRecord(
            alert_id=sample_alert.id, price=99.00, availability="available"
        )
        db_session.add(record)
        db_session.commit()

        assert record.alert.name == sample_alert.name
        assert record.alert.id == sample_alert.id


class TestNotificationLog:
    """Tests for NotificationLog model."""

    def test_create_notification_log(self, db_session, sample_alert):
        """Test creating a notification log."""
        log = NotificationLog(
            alert_id=sample_alert.id,
            trigger_reason="price_drop",
            price=85.00,
        )
        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.alert_id == sample_alert.id
        assert log.trigger_reason == "price_drop"
        assert log.price == 85.00
        assert isinstance(log.sent_at, datetime)

    def test_notification_log_relationship(self, db_session, sample_alert):
        """Test notification log relationship back to alert."""
        log = NotificationLog(
            alert_id=sample_alert.id,
            trigger_reason="first_time",
            price=90.00,
        )
        db_session.add(log)
        db_session.commit()

        assert log.alert.name == sample_alert.name
        assert log.alert.id == sample_alert.id
