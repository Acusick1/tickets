"""StubHub ticket price scraper."""
import logging
import re
from typing import Dict

from .base import BaseScraper

logger = logging.getLogger(__name__)


class StubHubScraper(BaseScraper):
    """Scraper for StubHub ticket prices."""

    def scrape(self, url: str) -> Dict:
        """Scrape ticket prices from StubHub.

        Args:
            url: StubHub event URL

        Returns:
            Dictionary with price, availability, and raw_data
        """
        assert self.page is not None, "Page not initialized. Use scraper within context manager."

        logger.info(f"Scraping StubHub: {url}")

        # Navigate to the page
        self.page.goto(url, wait_until="domcontentloaded")
        self.random_delay(2, 4)

        price = None
        availability = "unknown"
        raw_data = {}

        try:
            # Wait for initial page load
            self.page.wait_for_load_state("domcontentloaded", timeout=15000)

            # StubHub is heavily JavaScript-based - wait for React app to render
            logger.debug("Waiting 10 seconds for JavaScript to load ticket listings...")
            self.page.wait_for_timeout(10000)

            # Try to scroll down to trigger lazy loading of tickets
            try:
                self.page.evaluate("window.scrollTo(0, 800)")
                self.page.wait_for_timeout(3000)  # Wait after scroll
                logger.debug("Scrolled page to trigger content loading")
            except Exception as e:
                logger.debug(f"Could not scroll page: {e}")

            # Get all text content from the page
            page_text = self.page.inner_text("body")

            # Extract all prices from the page text using regex (support $ and £)
            # Try USD first
            price_matches = re.findall(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', page_text)
            currency = "USD"

            # If no USD prices found, try GBP
            if not price_matches:
                price_pattern = r'£\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
                price_matches = re.findall(price_pattern, page_text)
                currency = "GBP"

            if price_matches:
                # Convert first price found (usually the lowest)
                price_str = price_matches[0].replace(",", "")
                price = float(price_str)
                currency_symbol = "$" if currency == "USD" else "£"
                raw_data["price_text"] = f"{currency_symbol}{price_matches[0]}"
                raw_data["currency"] = currency
                raw_data["all_prices_found"] = [
                    f"{currency_symbol}{p}" for p in price_matches[:10]
                ]
                num_prices = len(price_matches)
                logger.info(
                    f"Found price: {currency_symbol}{price} {currency} "
                    f"(from {num_prices} prices on page)"
                )
            else:
                logger.warning("No prices found in page text")

            # Check for sold out or no tickets available
            sold_out_indicators = [
                "sold out",
                "no tickets available",
                "event has ended",
                "no longer available",
            ]

            page_text = self.page.inner_text("body").lower()
            for indicator in sold_out_indicators:
                if indicator in page_text:
                    availability = "sold_out"
                    logger.info(f"Event appears to be sold out (found '{indicator}')")
                    break

            if availability != "sold_out":
                if price is not None:
                    availability = "available"
                else:
                    availability = "unknown"

            # Store additional debug info
            raw_data["url"] = url
            raw_data["page_title"] = self.page.title()

        except Exception as e:
            logger.error(f"Error scraping StubHub: {e}", exc_info=True)
            availability = "error"
            raw_data["error"] = str(e)

        return {"price": price, "availability": availability, "raw_data": raw_data}
