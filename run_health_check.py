#!/usr/bin/env python3
"""Run health checks on all scrapers."""
import logging
import sys
import argparse
from pathlib import Path

from src.health_check import ScraperHealthChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run health checks."""
    parser = argparse.ArgumentParser(description="Run scraper health checks")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browsers in headless mode (default: True)",
    )
    parser.add_argument(
        "--save-report",
        action="store_true",
        default=True,
        help="Save report to JSON file (default: True)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="Timeout for scraping in milliseconds (default: 30000)",
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Starting Scraper Health Checks")
    logger.info("=" * 70)

    # Run health checks
    checker = ScraperHealthChecker(headless=args.headless, timeout=args.timeout)
    results = checker.check_all_scrapers()

    # Generate report
    report = checker.generate_report(results)

    # Print summary
    checker.print_summary(results)

    # Save report to file
    if args.save_report:
        Path("data").mkdir(exist_ok=True)
        checker.save_report(report)

    # Exit with appropriate code (0 = success, 1 = failure)
    all_passed = report["summary"]["failed"] == 0
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
