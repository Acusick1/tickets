"""StubHub ticket price scraper."""
import logging

from .base import BaseScraper, ScrapeResult

logger = logging.getLogger(__name__)


class StubHubScraper(BaseScraper):
    """Scraper for StubHub ticket prices."""

    def scrape(self, url: str) -> ScrapeResult:
        """Scrape ticket prices from StubHub.

        Args:
            url: StubHub event URL

        Returns:
            ScrapeResult with price, availability, and raw_data
        """
        return self._scrape_price_page(
            url=url,
            wait_time_ms=10000,  # StubHub React app render time
            scroll_to_trigger_loading=True,
            scroll_position="800",  # Scroll to 800px instead of bottom
            currencies=("USD", "GBP"),
            sold_out_indicators=[
                "sold out",
                "no tickets available",
                "event has ended",
                "no longer available",
            ],
        )
