"""Pytest fixtures for testing."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Alert, PriceRecord, NotificationLog
from src.notifier import EmailNotifier


@pytest.fixture
def db_session():
    """Provide a test database session with in-memory SQLite."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()


@pytest.fixture
def sample_alert(db_session):
    """Create a sample alert for testing."""
    alert = Alert(
        name="Test Event",
        source="ticketmaster",
        source_url="https://www.ticketmaster.com/test",
        target_price=100.00,
        is_active=True,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


@pytest.fixture
def sample_alert_with_history(db_session):
    """Create an alert with price history."""
    alert = Alert(
        name="Event with History",
        source="stubhub",
        source_url="https://www.stubhub.com/test",
        target_price=150.00,
        is_active=True,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    # Add price records
    prices = [200.00, 180.00, 160.00, 140.00, 120.00]
    for price in prices:
        record = PriceRecord(
            alert_id=alert.id,
            price=price,
            availability="available",
            raw_data={"test": True},
        )
        db_session.add(record)

    db_session.commit()
    return alert


@pytest.fixture
def notified_alert(db_session):
    """Create an alert that has already been notified."""
    alert = Alert(
        name="Previously Notified Event",
        source="viagogo",
        source_url="https://www.viagogo.com/test",
        target_price=100.00,
        last_notified_price=95.00,
        is_active=True,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


@pytest.fixture
def mock_notifier(mocker):
    """Mock email notifier for testing."""
    notifier = EmailNotifier(
        smtp_host="smtp.test.com",
        smtp_port=587,
        sender_email="test@test.com",
        sender_password="password",
        recipient_email="recipient@test.com",
    )

    # Mock the send_notification method
    mocker.patch.object(notifier, "send_notification", return_value=True)
    mocker.patch.object(notifier, "test_connection", return_value=True)

    return notifier


@pytest.fixture
def mock_scraper_result():
    """Provide a mock scraper result."""
    return {
        "price": 89.99,
        "availability": "available",
        "raw_data": {"page_title": "Test Event", "url": "https://test.com"},
    }


@pytest.fixture
def mock_scraper(mocker, mock_scraper_result):
    """Mock scraper for testing without network calls."""
    from src.scrapers.base import BaseScraper

    # Create a mock scraper
    scraper_instance = mocker.MagicMock(spec=BaseScraper)
    scraper_instance.scrape_with_retry.return_value = mock_scraper_result
    scraper_instance.__enter__.return_value = scraper_instance
    scraper_instance.__exit__.return_value = None

    return scraper_instance


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "email": {
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "sender_email": "test@test.com",
            "sender_password": "password",
            "recipient_email": "recipient@test.com",
        },
        "scraping": {
            "interval_minutes": 15,
            "timeout_seconds": 30,
            "headless": True,
            "user_agent": "Test User Agent",
        },
    }


@pytest.fixture
def test_alerts_config():
    """Provide test alerts configuration."""
    return [
        {
            "name": "Test Alert 1",
            "source": "ticketmaster",
            "url": "https://www.ticketmaster.com/test1",
            "target_price": 100.00,
            "active": True,
        },
        {
            "name": "Test Alert 2",
            "source": "stubhub",
            "url": "https://www.stubhub.com/test2",
            "target_price": 200.00,
            "active": True,
        },
    ]


@pytest.fixture
def mock_smtp(mocker):
    """Mock SMTP server for email testing."""
    mock_server = mocker.MagicMock()
    mock_server.__enter__ = mocker.MagicMock(return_value=mock_server)
    mock_server.__exit__ = mocker.MagicMock(return_value=None)
    mock_smtp_class = mocker.patch("smtplib.SMTP", return_value=mock_server)
    return mock_server


@pytest.fixture
def mock_playwright(mocker):
    """Mock Playwright browser for scraper testing."""
    mock_page = mocker.MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.inner_text.return_value = "Test Page Content $50"
    mock_page.title.return_value = "Test Event"

    mock_browser = mocker.MagicMock()
    mock_browser.new_context.return_value.new_page.return_value = mock_page

    mock_playwright_obj = mocker.MagicMock()
    mock_playwright_obj.chromium.launch.return_value = mock_browser

    mocker.patch(
        "src.scrapers.base.sync_playwright",
        return_value=mocker.MagicMock(start=lambda: mock_playwright_obj),
    )

    return mock_page
