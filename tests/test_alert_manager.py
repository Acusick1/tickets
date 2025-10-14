"""Tests for alert manager."""
import pytest

from src.alert_manager import AlertManager
from src.models import Alert, PriceRecord, NotificationLog


class TestAlertManager:
    """Tests for AlertManager class."""

    def test_initialization(self, db_session, mock_notifier):
        """Test alert manager initialization."""
        manager = AlertManager(db_session, mock_notifier)
        assert manager.db_session == db_session
        assert manager.notifier == mock_notifier

    def test_get_scraper(self, db_session, mock_notifier):
        """Test getting the correct scraper for each source."""
        manager = AlertManager(db_session, mock_notifier)

        ticketmaster_scraper = manager.get_scraper("ticketmaster")
        stubhub_scraper = manager.get_scraper("stubhub")
        viagogo_scraper = manager.get_scraper("viagogo")

        assert ticketmaster_scraper is not None
        assert stubhub_scraper is not None
        assert viagogo_scraper is not None

    def test_get_scraper_unknown_source(self, db_session, mock_notifier):
        """Test error handling for unknown source."""
        manager = AlertManager(db_session, mock_notifier)

        with pytest.raises(ValueError):
            manager.get_scraper("unknown_source")

    def test_process_alert_success(
        self, db_session, sample_alert, mock_notifier, mocker, mock_scraper
    ):
        """Test successful alert processing."""
        manager = AlertManager(db_session, mock_notifier)

        # Mock get_scraper to return our mock scraper
        mocker.patch.object(manager, "get_scraper", return_value=mock_scraper)

        # Process the alert
        result = manager.process_alert(sample_alert)

        assert result is True
        assert sample_alert.last_checked is not None

        # Verify price record was created
        price_records = (
            db_session.query(PriceRecord)
            .filter(PriceRecord.alert_id == sample_alert.id)
            .all()
        )
        assert len(price_records) == 1
        assert price_records[0].price == 89.99

    def test_notification_logic_first_time(
        self, db_session, sample_alert, mock_notifier
    ):
        """Test notification logic for first time below threshold."""
        manager = AlertManager(db_session, mock_notifier)

        # Price below threshold, no previous notification
        should_notify, reason = manager._should_notify(sample_alert, 95.00)

        assert should_notify is True
        assert reason == "first_time"

    def test_notification_logic_price_drop(
        self, db_session, notified_alert, mock_notifier
    ):
        """Test notification logic for price drop."""
        manager = AlertManager(db_session, mock_notifier)

        # Price drops further below last notified price
        should_notify, reason = manager._should_notify(notified_alert, 90.00)

        assert should_notify is True
        assert reason == "price_drop"

    def test_notification_logic_no_notify_same_price(
        self, db_session, notified_alert, mock_notifier
    ):
        """Test no notification when price is same."""
        manager = AlertManager(db_session, mock_notifier)

        # Price is same as last notified
        should_notify, reason = manager._should_notify(notified_alert, 95.00)

        assert should_notify is False
        assert reason == ""

    def test_notification_logic_no_notify_price_increase(
        self, db_session, notified_alert, mock_notifier
    ):
        """Test no notification when price increases."""
        manager = AlertManager(db_session, mock_notifier)

        # Price increased (but still below target)
        should_notify, reason = manager._should_notify(notified_alert, 98.00)

        assert should_notify is False

    def test_notification_logic_no_notify_above_threshold(
        self, db_session, sample_alert, mock_notifier
    ):
        """Test no notification when price is above threshold."""
        manager = AlertManager(db_session, mock_notifier)

        # Price above target threshold
        should_notify, reason = manager._should_notify(sample_alert, 105.00)

        assert should_notify is False

    def test_send_notification(self, db_session, sample_alert, mock_notifier):
        """Test sending notification."""
        manager = AlertManager(db_session, mock_notifier)

        manager._send_notification(sample_alert, 95.00, "first_time")

        # Verify notification was sent
        mock_notifier.send_notification.assert_called_once()

        # Verify last_notified_price was updated
        assert sample_alert.last_notified_price == 95.00

        # Verify notification log was created
        logs = (
            db_session.query(NotificationLog)
            .filter(NotificationLog.alert_id == sample_alert.id)
            .all()
        )
        assert len(logs) == 1
        assert logs[0].trigger_reason == "first_time"
        assert logs[0].price == 95.00

    def test_process_all_alerts(
        self, db_session, sample_alert, mock_notifier, mocker, mock_scraper
    ):
        """Test processing all active alerts."""
        # Create another alert
        alert2 = Alert(
            name="Test Event 2",
            source="stubhub",
            source_url="https://www.stubhub.com/test",
            target_price=150.00,
            is_active=True,
        )
        db_session.add(alert2)
        db_session.commit()

        manager = AlertManager(db_session, mock_notifier)
        mocker.patch.object(manager, "get_scraper", return_value=mock_scraper)

        # Process all alerts
        stats = manager.process_all_alerts()

        assert stats["total"] == 2
        assert stats["success"] == 2
        assert stats["failed"] == 0
