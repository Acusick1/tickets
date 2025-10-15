"""Health check system for scraper validation."""
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.scrapers.stubhub import StubHubScraper
from src.scrapers.ticketmaster import TicketmasterScraper
from src.scrapers.viagogo import ViagogoScraper

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    scraper_name: str
    url: str
    success: bool
    price_extracted: bool
    price_value: Optional[float]
    currency: Optional[str]
    availability: Optional[str]
    error_message: Optional[str]
    timestamp: str
    response_time_seconds: float


class ScraperHealthChecker:
    """Performs health checks on all scrapers."""

    # Test URLs for each scraper (real event pages with tickets available)
    # Using Lakers NBA games as they're stable, international, and available on all platforms
    TEST_URLS = {
        "ticketmaster": "https://www.ticketmaster.com/los-angeles-lakers-vs-milwaukee-bucks-los-angeles-california-01-09-2026/event/2C00630818590ACB",
        "stubhub": "https://www.stubhub.com/los-angeles-lakers-los-angeles-tickets-3-8-2026/event/159098523/",
        "viagogo": "https://www.viagogo.com/Sports-Tickets/Basketball/NBA/Los-Angeles-Lakers-Tickets/E-159128540",  # Warriors at Lakers Oct 21, 2025
    }

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize health checker.

        Args:
            headless: Whether to run browsers in headless mode
            timeout: Timeout for scraping operations in milliseconds
        """
        self.headless = headless
        self.timeout = timeout

    def check_scraper(self, scraper_name: str, scraper_class, url: str) -> HealthCheckResult:
        """Check a single scraper.

        Args:
            scraper_name: Name of the scraper
            scraper_class: Scraper class to instantiate
            url: URL to test scraping

        Returns:
            HealthCheckResult with test details
        """
        start_time = datetime.utcnow()
        error_message = None
        price_extracted = False
        price_value = None
        currency = None
        availability = None
        success = False

        try:
            logger.info(f"Testing {scraper_name} scraper with URL: {url}")

            scraper = scraper_class(headless=self.headless, timeout=self.timeout)

            with scraper:
                result = scraper.scrape(url)

                # Extract data from ScrapeResult
                price_value = result.price
                availability = result.availability
                currency = result.raw_data.currency

                if price_value is not None and price_value > 0:
                    price_extracted = True
                    success = True
                    logger.info(
                        f"✅ {scraper_name} health check passed: "
                        f"Price={price_value} {currency or ''}, "
                        f"Availability={availability}"
                    )
                else:
                    error_message = "Price is None or zero"
                    logger.warning(f"⚠️  {scraper_name} returned no valid price")

        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ {scraper_name} health check failed: {e}")

        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()

        return HealthCheckResult(
            scraper_name=scraper_name,
            url=url,
            success=success,
            price_extracted=price_extracted,
            price_value=price_value,
            currency=currency,
            availability=availability,
            error_message=error_message,
            timestamp=start_time.isoformat(),
            response_time_seconds=round(response_time, 2),
        )

    def check_all_scrapers(self) -> List[HealthCheckResult]:
        """Run health checks on all scrapers.

        Returns:
            List of health check results
        """
        results = []

        # Check Ticketmaster
        results.append(self.check_scraper("Ticketmaster", TicketmasterScraper, self.TEST_URLS["ticketmaster"]))

        # Check StubHub
        results.append(
            self.check_scraper("StubHub", StubHubScraper, self.TEST_URLS["stubhub"])
        )

        # Check Viagogo
        results.append(
            self.check_scraper("Viagogo", ViagogoScraper, self.TEST_URLS["viagogo"])
        )

        return results

    def generate_report(self, results: List[HealthCheckResult]) -> Dict:
        """Generate a summary report of health check results.

        Args:
            results: List of health check results

        Returns:
            Dictionary with summary statistics
        """
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_scrapers_tested": total,
                "passed": passed,
                "failed": failed,
                "success_rate": round((passed / total * 100) if total > 0 else 0, 2),
            },
            "results": [asdict(r) for r in results],
        }

        return report

    def save_report(self, report: Dict, filepath: str = "data/health_check_report.json"):
        """Save health check report to file.

        Args:
            report: Report dictionary
            filepath: Path to save the report
        """
        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Health check report saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save health check report: {e}")

    def print_summary(self, results: List[HealthCheckResult]):
        """Print a human-readable summary of results.

        Args:
            results: List of health check results
        """
        print("\n" + "=" * 70)
        print("SCRAPER HEALTH CHECK SUMMARY")
        print("=" * 70)

        for result in results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"\n{status} - {result.scraper_name}")
            print(f"  URL: {result.url}")
            print(f"  Response time: {result.response_time_seconds}s")

            if result.success:
                currency_str = f" {result.currency}" if result.currency else ""
                print(f"  Price: {result.price_value}{currency_str}")
                print(f"  Availability: {result.availability}")
            else:
                print(f"  Error: {result.error_message}")

        print("\n" + "=" * 70)
        passed = sum(1 for r in results if r.success)
        total = len(results)
        print(f"Overall: {passed}/{total} scrapers passed")
        print("=" * 70 + "\n")
