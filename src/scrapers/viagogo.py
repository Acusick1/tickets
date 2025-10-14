"""Viagogo ticket price scraper."""
import logging
import re
from typing import Dict

from .base import BaseScraper

logger = logging.getLogger(__name__)


class ViagogoScraper(BaseScraper):
    """Scraper for Viagogo ticket prices."""

    def scrape(self, url: str) -> Dict:
        """Scrape ticket prices from Viagogo.

        Args:
            url: Viagogo event URL

        Returns:
            Dictionary with price, availability, and raw_data
        """
        assert self.page is not None, "Page not initialized. Use scraper within context manager."

        logger.info(f"Scraping Viagogo: {url}")

        # Navigate to the page and wait for DOM (like Ticketmaster)
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait additional time for JavaScript to load ticket listings
        logger.debug("Waiting 12 seconds for JavaScript to render prices...")
        self.page.wait_for_timeout(12000)

        # Scroll to trigger lazy loading
        try:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(2000)
            logger.debug("Scrolled page to trigger content loading")
        except Exception as e:
            logger.debug(f"Could not scroll page: {e}")

        price = None
        availability = "unknown"
        raw_data = {}
        currency = None

        try:
            # Get all text content from the page
            page_text = self.page.inner_text("body")

            # Extract all prices from the page text using regex (various currencies)
            # Try USD first
            price_matches = re.findall(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', page_text)
            currency = "USD"

            # If no USD, try GBP
            if not price_matches:
                gbp_pattern = r'£\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
                price_matches = re.findall(gbp_pattern, page_text)
                currency = "GBP"

            # If no GBP, try EUR
            if not price_matches:
                eur_pattern = r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
                price_matches = re.findall(eur_pattern, page_text)
                currency = "EUR"

            if price_matches:
                # Convert first price found (usually the lowest)
                price_str = price_matches[0].replace(",", "")
                price = float(price_str)
                currency_symbol = {"USD": "$", "GBP": "£", "EUR": "€"}[currency]
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
                "no longer on sale",
            ]

            page_text_lower = page_text.lower()
            for indicator in sold_out_indicators:
                if indicator in page_text_lower:
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
            logger.error(f"Error scraping Viagogo: {e}", exc_info=True)
            availability = "error"
            raw_data["error"] = str(e)

        return {"price": price, "availability": availability, "raw_data": raw_data}
