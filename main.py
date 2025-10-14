"""Main entry point for the ticket price scraper."""
import logging
import signal
import sys
from pathlib import Path

from src.alert_manager import AlertManager
from src.config import load_alerts, load_settings, sync_alerts_to_db
from src.models import init_db
from src.notifier import EmailNotifier
from src.scheduler import AlertScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/ticket_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutdown signal received, stopping...")
    sys.exit(0)


def main():
    """Main application entry point."""
    logger.info("=" * 60)
    logger.info("Starting Ticket Price Scraper")
    logger.info("=" * 60)

    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    Path("data/errors").mkdir(exist_ok=True)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        settings = load_settings("config/settings.yaml")
        alerts_config = load_alerts("config/alerts.yaml")

        # Initialize database
        logger.info("Initializing database...")
        db_session = init_db("sqlite:///data/tickets.db")

        # Sync alerts to database
        sync_alerts_to_db(alerts_config, db_session)

        # Initialize email notifier
        logger.info("Initializing email notifier...")
        email_config = settings.get("email", {})
        notifier = EmailNotifier(
            smtp_host=email_config.get("smtp_host"),
            smtp_port=email_config.get("smtp_port"),
            sender_email=email_config.get("sender_email"),
            sender_password=email_config.get("sender_password"),
            recipient_email=email_config.get("recipient_email"),
        )

        # Test email connection
        if notifier.test_connection():
            logger.info("Email notifier configured successfully")
        else:
            logger.warning("Email notifier test failed, notifications may not work")

        # Initialize alert manager
        logger.info("Initializing alert manager...")
        scraper_config = {
            "headless": settings.get("scraping", {}).get("headless", True),
            "timeout": settings.get("scraping", {}).get("timeout_seconds", 30) * 1000,
            "user_agent": settings.get("scraping", {}).get("user_agent"),
        }
        alert_manager = AlertManager(db_session, notifier, scraper_config)

        # Initialize and start scheduler
        logger.info("Starting scheduler...")
        interval = settings.get("scraping", {}).get("interval_minutes", 15)
        scheduler = AlertScheduler(alert_manager, interval_minutes=interval)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start scheduler
        scheduler.start()

        logger.info("=" * 60)
        logger.info("Ticket Price Scraper is now running")
        logger.info(f"Checking alerts every {interval} minutes")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Keep the main thread alive
        import time

        while True:
            time.sleep(1)

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Please create config/alerts.yaml and config/settings.yaml")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
