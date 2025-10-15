"""Viagogo ticket price scraper."""
import logging

from .base import BaseScraper, ScrapeResult

logger = logging.getLogger(__name__)


class ViagogoScraper(BaseScraper):
    """Scraper for Viagogo ticket prices."""

    def scrape(self, url: str) -> ScrapeResult:
        """Scrape ticket prices from Viagogo.

        Args:
            url: Viagogo event URL

        Returns:
            ScrapeResult with price, availability, and raw_data
        """
        return self._scrape_price_page(
            url=url,
            wait_time_ms=12000,  # Viagogo JavaScript render time
            scroll_to_trigger_loading=True,
            scroll_position="document.body.scrollHeight",
            currencies=("USD", "GBP", "EUR"),  # Viagogo supports EUR
            sold_out_indicators=[
                "sold out",
                "no tickets available",
                "event has ended",
                "no longer on sale",
                "view 0 listings",  # Viagogo-specific
                "showing 0 of 0",   # Viagogo-specific
            ],
        )
