"""Tests for scrapers."""

from src.scrapers import StubHubScraper, TicketmasterScraper, ViagogoScraper
from src.scrapers.base import ScrapeResult


class TestBaseScraper:
    """Tests for base scraper functionality."""

    def test_initialization(self):
        """Test scraper initialization."""
        # Can't directly instantiate abstract class, so we'll test with concrete impl
        scraper = TicketmasterScraper(headless=True, timeout=30000)
        assert scraper.headless is True
        assert scraper.timeout == 30000
        assert scraper.user_agent is not None

    def test_random_delay(self, mocker):
        """Test random delay functionality."""
        scraper = TicketmasterScraper()
        mock_sleep = mocker.patch("time.sleep")

        scraper.random_delay(1, 2)

        # Verify sleep was called with a value between 1 and 2
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 1 <= delay <= 2


class TestTicketmasterScraper:
    """Tests for Ticketmaster scraper."""

    def test_scrape_with_mock(self, mocker, mock_playwright):
        """Test scraping with mocked Playwright."""
        # Setup mock to return price element
        mock_element = mocker.MagicMock()
        mock_element.inner_text.return_value = "From $89.99"
        mock_playwright.query_selector_all.return_value = [mock_element]
        mock_playwright.inner_text.return_value = "event page content"

        scraper = TicketmasterScraper(headless=True)

        with scraper:
            result = scraper.scrape("https://www.ticketmaster.com/test")

        assert result is not None
        assert isinstance(result, ScrapeResult)
        assert result.price is not None
        assert result.availability is not None
        assert result.raw_data is not None

    def test_scrape_sold_out(self, mocker, mock_playwright):
        """Test sold out detection."""
        mock_playwright.query_selector_all.return_value = []
        # Mock inner_text to return sold out message with a price
        mock_playwright.inner_text.return_value = "This event is sold out $50"
        # Mock content() for fallback (should not be called since text has price)
        mock_playwright.content.return_value = "This event is sold out $50"

        scraper = TicketmasterScraper(headless=True)

        with scraper:
            result = scraper.scrape("https://www.ticketmaster.com/test")

        assert result.availability == "sold_out"


class TestStubHubScraper:
    """Tests for StubHub scraper."""

    def test_scrape_with_mock(self, mocker, mock_playwright):
        """Test scraping with mocked Playwright."""
        mock_element = mocker.MagicMock()
        mock_element.inner_text.return_value = "$125.50"
        mock_playwright.query_selector_all.return_value = [mock_element]
        mock_playwright.inner_text.return_value = "event page"

        scraper = StubHubScraper(headless=True)

        with scraper:
            result = scraper.scrape("https://www.stubhub.com/test")

        assert result is not None
        assert isinstance(result, ScrapeResult)
        assert result.price is not None
        assert result.availability is not None

    def test_scrape_no_tickets(self, mocker, mock_playwright):
        """Test no tickets available detection."""
        mock_playwright.query_selector_all.return_value = []
        mock_playwright.inner_text.return_value = "no tickets available"

        scraper = StubHubScraper(headless=True)

        with scraper:
            result = scraper.scrape("https://www.stubhub.com/test")

        assert result.availability == "sold_out"


class TestViagogoScraper:
    """Tests for Viagogo scraper."""

    def test_scrape_with_mock(self, mocker, mock_playwright):
        """Test scraping with mocked Playwright."""
        mock_element = mocker.MagicMock()
        mock_element.inner_text.return_value = "£75.00"
        mock_playwright.query_selector_all.return_value = [mock_element]
        mock_playwright.inner_text.return_value = "event page"

        scraper = ViagogoScraper(headless=True)

        with scraper:
            result = scraper.scrape("https://www.viagogo.com/test")

        assert result is not None
        assert isinstance(result, ScrapeResult)
        assert result.price is not None
        assert result.availability is not None

    def test_scrape_with_retry(self, mocker, mock_playwright):
        """Test retry logic with tenacity."""
        mock_element = mocker.MagicMock()
        mock_element.inner_text.return_value = "€99.99"
        mock_playwright.query_selector_all.return_value = [mock_element]
        mock_playwright.inner_text.return_value = "event page"

        scraper = ViagogoScraper(headless=True)

        with scraper:
            result = scraper.scrape_with_retry("https://www.viagogo.com/test")

        assert result is not None
        assert isinstance(result, ScrapeResult)
        assert result.price is not None
