"""Ticketmaster ticket price scraper."""
import logging

from .base import BaseScraper, ScrapeResult

logger = logging.getLogger(__name__)


class TicketmasterScraper(BaseScraper):
    """Scraper for Ticketmaster ticket prices."""

    def scrape(self, url: str) -> ScrapeResult:
        """Scrape ticket prices from Ticketmaster.

        Args:
            url: Ticketmaster event URL

        Returns:
            ScrapeResult with price, availability, and raw_data
        """
        return self._scrape_price_page(
            url=url,
            wait_time_ms=15000,  # Wait longer for Ticketmaster's JavaScript
            scroll_to_trigger_loading=True,
            scroll_position="document.body.scrollHeight",
            currencies=("USD", "GBP"),
            sold_out_indicators=[
                "sold out",
                "no tickets available",
                "event has passed",
                "unavailable",
            ],
        )
