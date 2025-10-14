"""Base scraper class with Playwright initialization."""
import logging
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from playwright.sync_api import Browser, Page, sync_playwright

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base scraper with Playwright setup and anti-detection measures."""

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

    @abstractmethod
    def scrape(self, url: str) -> Dict:
        """Scrape ticket prices from the given URL.

        Args:
            url: The URL to scrape

        Returns:
            Dictionary with keys:
                - price: float or None if not available
                - availability: str (e.g., "available", "sold_out", "limited")
                - raw_data: dict with additional data for debugging
        """
        pass

    def scrape_with_retry(
        self, url: str, max_retries: int = 3, retry_delay: float = 5.0
    ) -> Dict:
        """Scrape with retry logic.

        Args:
            url: The URL to scrape
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Scrape result dictionary
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Scraping {url} (attempt {attempt + 1}/{max_retries})")
                result = self.scrape(url)
                logger.info(f"Successfully scraped {url}: {result}")
                return result
            except Exception as e:
                logger.error(
                    f"Scraping attempt {attempt + 1}/{max_retries} failed: {e}",
                    exc_info=True,
                )

                # Save debug information on last attempt
                if attempt == max_retries - 1:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    self.save_screenshot(f"data/errors/screenshot_{timestamp}.png")
                    self.save_html(f"data/errors/page_{timestamp}.html")

                    return {
                        "price": None,
                        "availability": "error",
                        "raw_data": {"error": str(e), "url": url},
                    }

                # Wait before retry
                time.sleep(retry_delay)

        return {
            "price": None,
            "availability": "error",
            "raw_data": {"error": "Max retries exceeded", "url": url},
        }
