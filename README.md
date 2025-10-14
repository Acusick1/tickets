# Ticket Price Scraper

[![Health check](https://github.com/Acusick1/tickets/actions/workflows/health-check.yml/badge.svg)](https://github.com/Acusick1/tickets/actions/workflows/health-check.yml)

A Python-based system that automatically monitors ticket prices from Ticketmaster, StubHub, and Viagogo, and sends email notifications when prices drop below your target thresholds.

## Features

- **Multi-source scraping**: Supports Ticketmaster, StubHub, and Viagogo
- **Smart notifications**: Only notifies when price drops below threshold or continues dropping
- **Price history**: Stores complete historical price data in SQLite database
- **Scheduled checks**: Automatically checks prices every 15 minutes (configurable)
- **Web dashboard**: Optional Flask-based dashboard to visualize price trends
- **Health checks**: Automated daily validation with email reports
- **Multi-currency**: Supports USD, GBP, and other currencies automatically
- **Anti-detection**: Built-in measures to avoid bot detection
- **Comprehensive tests**: 32 tests covering all major functionality

## Quick Start

### 1. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### 2. Configure Settings

Copy the example configuration files and edit them with your settings:

```bash
cp config/settings.yaml.example config/settings.yaml
cp config/alerts.yaml.example config/alerts.yaml
```

**config/settings.yaml**: Edit with your email credentials

```yaml
email:
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "your-email@gmail.com"
  sender_password: "your-app-password"  # Gmail App Password
  recipient_email: "your-email@gmail.com"

scraping:
  interval_minutes: 15
  timeout_seconds: 30
  headless: true
```

**config/alerts.yaml**: Add your events to monitor

```yaml
alerts:
  - name: "Taylor Swift - Miami"
    source: "ticketmaster"
    url: "https://www.ticketmaster.com/event/..."
    target_price: 150.00
    active: true
```

### 3. Verify Setup

```bash
# Verify all dependencies and configuration
uv run python verify_setup.py
```

This will check:

- All required files are present
- Dependencies are installed
- Configuration files exist

### 4. Run the Application

```bash
# Start the price monitoring system
uv run python main.py

# In a separate terminal, start the dashboard (optional)
uv run python -m src.dashboard.app
```

The dashboard will be available on [port 5000](http://127.0.0.1:5000)

## Gmail Setup

For Gmail, you need to use an App Password:

1. Enable 2-factor authentication on your Google account
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the App Password in `config/settings.yaml`

## Notification Logic

The system uses smart notification logic to avoid spam:

1. **First time below threshold**: Sends notification when price first drops below target
2. **Price continues dropping**: Sends notification only when price drops lower than last notified price
3. **Price stable or increases**: No notification (even if still below target)

Example:

- Target: $100
- Current: $120 → No notification
- Current: $95 → **Notification** (first time below)
- Current: $90 → **Notification** (price dropped further)
- Current: $92 → No notification (price increased)
- Current: $85 → **Notification** (price dropped again)

## Database Schema

**alerts**: Event monitoring configuration

- id, name, source, source_url, target_price
- last_notified_price, is_active, last_checked, created_at

**price_records**: Historical price data

- id, alert_id (FK), price, availability, timestamp, raw_data (JSON)

**notification_logs**: Notification history

- id, alert_id (FK), sent_at, trigger_reason, price

### Configuration

Edit test URLs in `src/health_check.py`:

```python
TEST_URLS = {
    "ticketmaster": "https://www.ticketmaster.com/...",
    "stubhub": "https://www.stubhub.com/...",
    "viagogo": "https://www.viagogo.com/...",
}
```

**Important:** Use event URLs that won't expire soon (months in the future).

## Development

### Adding a new ticket source

1. Create a new scraper in `src/scrapers/`:

```python
from .base import BaseScraper

class NewSourceScraper(BaseScraper):
    def scrape(self, url: str) -> Dict:
        # Implement scraping logic
        return {
            "price": price,
            "availability": "available",
            "raw_data": {}
        }
```

2. Register in `src/alert_manager.py`:

```python
scraper_map = {
    "newsource": NewSourceScraper,
}
```

3. Add tests in `tests/test_scrapers.py`
