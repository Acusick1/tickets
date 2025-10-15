"""Base scraper class with Playwright initialization."""
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from playwright.sync_api import Browser, Page, sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class RawScrapeData:
    """Raw data captured during scraping for debugging."""

    url: str
    page_title: str
    price_text: Optional[str] = None
    currency: Optional[str] = None
    all_prices_found: Optional[List[str]] = None
    error: Optional[str] = None


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""

    price: Optional[float]
    availability: str
    raw_data: RawScrapeData


@dataclass
class CurrencyConfig:
    """Currency configuration for price extraction."""

    code: str
    symbol: str
    pattern: str


class BaseScraper(ABC):
    """Abstract base scraper with Playwright setup and anti-detection measures."""

    # Currency configurations
    CURRENCIES = {
        "USD": CurrencyConfig(
            code="USD",
            symbol="$",
            pattern=r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ),
        "GBP": CurrencyConfig(
            code="GBP",
            symbol="£",
            pattern=r'£\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ),
        "EUR": CurrencyConfig(
            code="EUR",
            symbol="€",
            pattern=r'€\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ),
    }

    # Default sold out indicators
    DEFAULT_SOLD_OUT_INDICATORS = [
        "sold out",
        "no tickets available",
        "event has passed",
        "event has ended",
        "unavailable",
        "no longer available",
        "no longer on sale",
    ]

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        user_agent: Optional[str] = None,
    ) -> None:
        """Initialize the scraper.

        Args:
            headless: Run browser in headless mode
            timeout: Timeout in milliseconds for page operations
            user_agent: Custom user agent string
        """
        self.headless = headless
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit."""
        self.stop()

    def start(self) -> None:
        """Start Playwright and browser."""
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()

        # Configure launch args
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]

        # For non-headless mode in WSL, disable GPU to avoid transparent window issues
        if not self.headless:
            launch_args.extend([
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-dev-shm-usage",
            ])

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        context = self.browser.new_context(
            user_agent=self.user_agent,
            viewport={"width": 1920, "height": 1080},
        )

        self.page = context.new_page()
        self.page.set_default_timeout(self.timeout)

        # Anti-detection: remove webdriver property
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    def stop(self) -> None:
        """Stop browser and Playwright."""
        logger.info("Stopping browser...")
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def random_delay(
        self, min_seconds: float = 2.0, max_seconds: float = 5.0
    ) -> None:
        """Add a random delay to avoid detection.

        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def save_screenshot(self, filename: str) -> None:
        """Save a screenshot for debugging.

        Args:
            filename: Path to save the screenshot
        """
        if self.page:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=filename, full_page=True)
            logger.info(f"Screenshot saved to {filename}")

    def save_html(self, filename: str) -> None:
        """Save page HTML for debugging.

        Args:
            filename: Path to save the HTML
        """
        if self.page:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                f.write(self.page.content())
            logger.info(f"HTML saved to {file_path}")

    def _scrape_price_page(
        self,
        url: str,
        wait_time_ms: int = 10000,
        scroll_to_trigger_loading: bool = True,
        scroll_position: str = "document.body.scrollHeight",
        currencies: Tuple[str, ...] = ("USD", "GBP"),
        sold_out_indicators: Optional[List[str]] = None,
    ) -> ScrapeResult:
        """Common scraping logic for price extraction.

        Args:
            url: The URL to scrape
            wait_time_ms: Milliseconds to wait for JavaScript to render
            scroll_to_trigger_loading: Whether to scroll to trigger lazy loading
            scroll_position: JavaScript expression for scroll position
            currencies: Tuple of currency codes to try (in order)
            sold_out_indicators: List of strings indicating sold out status

        Returns:
            ScrapeResult with price, availability, and raw_data
        """
        assert self.page is not None, "Page not initialized. Use scraper within context manager."

        logger.info(f"Scraping: {url}")

        # Navigate and wait for page to load
        self._navigate_and_wait(url, wait_time_ms)

        # Scroll to trigger lazy loading if requested
        if scroll_to_trigger_loading:
            self._scroll_page(scroll_position)

        # Extract page content
        page_text = self._get_page_text()

        # Extract price information
        price, currency_code, price_matches = self._extract_price(page_text, currencies)

        # Determine availability
        availability = self._check_availability(
            page_text,
            price,
            sold_out_indicators or self.DEFAULT_SOLD_OUT_INDICATORS,
        )

        # Build raw data
        raw_data = self._build_raw_data(url, price_matches, currency_code)

        return ScrapeResult(price=price, availability=availability, raw_data=raw_data)

    def _navigate_and_wait(self, url: str, wait_time_ms: int) -> None:
        """Navigate to URL and wait for content to load."""
        assert self.page is not None
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        logger.debug(f"Waiting {wait_time_ms}ms for JavaScript to load...")
        self.page.wait_for_timeout(wait_time_ms)

    def _scroll_page(self, scroll_position: str) -> None:
        """Scroll page to trigger lazy loading."""
        assert self.page is not None
        try:
            self.page.evaluate(f"window.scrollTo(0, {scroll_position})")
            self.page.wait_for_timeout(2000)
            logger.debug("Scrolled page to trigger content loading")
        except Exception as e:
            logger.debug(f"Could not scroll page: {e}")

    def _get_page_text(self) -> str:
        """Extract text content from page."""
        assert self.page is not None
        page_text = self.page.inner_text("body")

        # If no currency symbols found, try HTML content
        if not any(symbol in page_text for symbol in ["$", "£", "€"]):
            logger.debug("No currency symbols in text, trying HTML content")
            page_text = self.page.content()

        return page_text

    def _extract_price(
        self, page_text: str, currencies: Tuple[str, ...]
    ) -> Tuple[Optional[float], Optional[str], List[str]]:
        """Extract price from page text.

        Returns:
            Tuple of (price, currency_code, all_price_matches)
        """
        for currency_code in currencies:
            currency_config = self.CURRENCIES.get(currency_code)
            if not currency_config:
                continue

            price_matches = re.findall(currency_config.pattern, page_text)
            if price_matches:
                # Convert first price found (usually the lowest)
                price_str = price_matches[0].replace(",", "")
                price = float(price_str)
                logger.info(
                    f"Found price: {currency_config.symbol}{price} {currency_code} "
                    f"(from {len(price_matches)} prices on page)"
                )
                return price, currency_code, price_matches

        logger.warning("No prices found in page text")
        return None, None, []

    def _check_availability(
        self, page_text: str, price: Optional[float], indicators: List[str]
    ) -> str:
        """Check if tickets are available or sold out."""
        page_text_lower = page_text.lower()
        for indicator in indicators:
            if indicator in page_text_lower:
                logger.info(f"Event appears to be sold out (found '{indicator}')")
                return "sold_out"

        return "available" if price is not None else "unknown"

    def _build_raw_data(
        self,
        url: str,
        price_matches: List[str],
        currency_code: Optional[str],
    ) -> RawScrapeData:
        """Build raw data for debugging."""
        assert self.page is not None

        price_text = None
        all_prices_found = None

        if price_matches and currency_code:
            currency_config = self.CURRENCIES[currency_code]
            price_text = f"{currency_config.symbol}{price_matches[0]}"
            all_prices_found = [
                f"{currency_config.symbol}{p}" for p in price_matches[:10]
            ]

        return RawScrapeData(
            url=url,
            page_title=self.page.title(),
            price_text=price_text,
            currency=currency_code,
            all_prices_found=all_prices_found,
        )

    @abstractmethod
    def scrape(self, url: str) -> ScrapeResult:
        """Scrape ticket prices from the given URL.

        Args:
            url: The URL to scrape

        Returns:
            ScrapeResult with price, availability, and raw_data
        """
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def scrape_with_retry(self, url: str) -> ScrapeResult:
        """Scrape with automatic retry logic using tenacity.

        Args:
            url: The URL to scrape

        Returns:
            ScrapeResult with price, availability, and raw_data

        Raises:
            Exception: If all retry attempts fail
        """
        logger.info(f"Scraping {url}")
        try:
            result = self.scrape(url)
            logger.info(f"Successfully scraped {url}")
            return result
        except Exception as e:
            logger.error(f"Scraping failed: {e}", exc_info=True)
            # Save debug information on error
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.save_screenshot(f"data/errors/screenshot_{timestamp}.png")
            self.save_html(f"data/errors/page_{timestamp}.html")
            raise
