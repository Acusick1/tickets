"""Alert manager for coordinating scraping, price tracking, and notifications."""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from .models import Alert, NotificationLog, PriceRecord
from .notifier import EmailNotifier
from .scrapers import StubHubScraper, TicketmasterScraper, ViagogoScraper
from .scrapers.base import BaseScraper, ScrapeResult

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerts, scraping, and notifications."""

    def __init__(
        self,
        db_session: Session,
        notifier: EmailNotifier,
        scraper_config: Optional[Dict] = None,
    ) -> None:
        """Initialize the alert manager.

        Args:
            db_session: SQLAlchemy database session
            notifier: EmailNotifier instance
            scraper_config: Configuration for scrapers (headless, timeout, etc.)
        """
        self.db_session = db_session
        self.notifier = notifier
        self.scraper_config = scraper_config or {}

    def get_scraper(self, source: str) -> BaseScraper:
        """Get the appropriate scraper for the given source.

        Args:
            source: Source name (ticketmaster, stubhub, viagogo)

        Returns:
            Scraper instance
        """
        scraper_map = {
            "ticketmaster": TicketmasterScraper,
            "stubhub": StubHubScraper,
            "viagogo": ViagogoScraper,
        }

        scraper_class = scraper_map.get(source.lower())
        if not scraper_class:
            raise ValueError(f"Unknown source: {source}")

        return scraper_class(**self.scraper_config)

    def _raw_data_to_dict(self, result: ScrapeResult) -> Dict:
        """Convert RawScrapeData to dictionary for database storage.

        Args:
            result: ScrapeResult containing raw_data

        Returns:
            Dictionary representation of raw data
        """
        raw_data = result.raw_data
        data_dict = {
            "url": raw_data.url,
            "page_title": raw_data.page_title,
        }

        # Add optional fields if they exist
        if raw_data.price_text:
            data_dict["price_text"] = raw_data.price_text
        if raw_data.currency:
            data_dict["currency"] = raw_data.currency
        if raw_data.all_prices_found:
            data_dict["all_prices_found"] = raw_data.all_prices_found
        if raw_data.error:
            data_dict["error"] = raw_data.error

        return data_dict

    def process_alert(self, alert: Alert) -> bool:
        """Process a single alert: scrape, store, and notify if needed.

        Args:
            alert: Alert instance to process

        Returns:
            True if processing succeeded, False otherwise
        """
        logger.info(f"Processing alert: {alert.name} (ID: {alert.id})")

        try:
            # Get the appropriate scraper
            scraper = self.get_scraper(alert.source)

            # Scrape the price with retry
            with scraper:
                result: ScrapeResult = scraper.scrape_with_retry(alert.source_url)

            current_price = result.price
            availability = result.availability
            raw_data_dict = self._raw_data_to_dict(result)

            # Update alert's last_checked timestamp
            alert.last_checked = datetime.now()

            # Only store price record if we successfully got a price
            if current_price is not None:
                price_record = PriceRecord(
                    alert_id=alert.id,
                    price=current_price,
                    availability=availability,
                    raw_data=raw_data_dict,
                )
                self.db_session.add(price_record)

                # Check if we should send a notification
                should_notify, reason = self._should_notify(alert, current_price)

                if should_notify:
                    logger.info(
                        f"Notification triggered for {alert.name}: {reason} "
                        f"(${current_price:.2f})"
                    )
                    self._send_notification(alert, current_price, reason)

                logger.info(
                    f"Successfully processed alert {alert.name}: "
                    f"price=${current_price:.2f}, availability={availability}"
                )
            else:
                # Scraping failed - log warning but don't crash
                logger.warning(
                    f"Could not extract price for {alert.name}. "
                    f"Availability: {availability}. "
                    f"The scraper may need updating or the page structure changed."
                )

            self.db_session.commit()
            return True

        except Exception as e:
            logger.error(f"Error processing alert {alert.name}: {e}", exc_info=True)
            self.db_session.rollback()
            return False

    def _should_notify(self, alert: Alert, current_price: float) -> Tuple[bool, str]:
        """Determine if a notification should be sent.

        Notification logic:
        1. If price < target_price AND last_notified_price is None: notify (first_time)
        2. If price < target_price AND price < last_notified_price: notify (price_drop)
        3. Otherwise: don't notify

        Args:
            alert: Alert instance
            current_price: Current scraped price

        Returns:
            Tuple of (should_notify, reason)
        """
        target_price = alert.target_price
        last_notified = alert.last_notified_price

        # Price is not below target
        if current_price >= target_price:
            logger.debug(
                f"Price ${current_price:.2f} is not below target ${target_price:.2f}"
            )
            return False, ""

        # First time below threshold
        if last_notified is None:
            logger.info(
                f"First time below target: ${current_price:.2f} < ${target_price:.2f}"
            )
            return True, "first_time"

        # Price continuing to drop
        if current_price < last_notified:
            logger.info(
                f"Price drop: ${last_notified:.2f} -> ${current_price:.2f} "
                f"(target: ${target_price:.2f})"
            )
            return True, "price_drop"

        # Price same or increased (but still below target) - no notification
        logger.debug(
            f"Price ${current_price:.2f} not lower than last notified "
            f"${last_notified:.2f}"
        )
        return False, ""

    def _send_notification(
        self, alert: Alert, current_price: float, reason: str
    ) -> None:
        """Send notification and update alert state.

        Args:
            alert: Alert instance
            current_price: Current price
            reason: Notification trigger reason
        """
        try:
            # Send email notification
            success = self.notifier.send_notification(
                alert_name=alert.name,
                current_price=current_price,
                target_price=alert.target_price,
                url=alert.source_url,
                trigger_reason=reason,
                previous_price=alert.last_notified_price,
            )

            if success:
                # Update alert's last notified price
                alert.last_notified_price = current_price

                # Log the notification
                notification_log = NotificationLog(
                    alert_id=alert.id,
                    trigger_reason=reason,
                    price=current_price,
                )
                self.db_session.add(notification_log)

                logger.info(
                    f"Notification sent and logged for {alert.name} "
                    f"at ${current_price:.2f}"
                )
            else:
                logger.error(f"Failed to send notification for {alert.name}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}", exc_info=True)

    def process_all_alerts(self) -> Dict[str, int]:
        """Process all active alerts.

        Returns:
            Dictionary with success/failure counts
        """
        logger.info("Processing all active alerts...")

        alerts = self.db_session.query(Alert).filter(Alert.is_active).all()

        stats = {"total": len(alerts), "success": 0, "failed": 0}

        for alert in alerts:
            if self.process_alert(alert):
                stats["success"] += 1
            else:
                stats["failed"] += 1

        logger.info(
            f"Processed {stats['total']} alerts: "
            f"{stats['success']} succeeded, {stats['failed']} failed"
        )

        return stats
