# Ticket Price Scraper

A Python-based system that automatically monitors ticket prices from Ticketmaster, StubHub, and Viagogo, and sends email notifications when prices drop below your target thresholds.

## Features

- **Multi-source scraping**: Supports Ticketmaster, StubHub, and Viagogo
- **Smart notifications**: Only notifies when price drops below threshold or continues dropping
- **Price history**: Stores complete historical price data in SQLite database
- **Scheduled checks**: Automatically checks prices every 15 minutes (configurable)
- **Web dashboard**: Optional Flask-based dashboard to visualize price trends
- **Health checks**: Automated daily scraper validation with email reports
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

The dashboard will be available at http://127.0.0.1:5000

### 5. Set Up Daily Health Checks (Recommended)

Health checks verify your scrapers are working correctly by testing them daily with real URLs via GitHub Actions.

**Quick setup:**

1. Edit test URLs in `src/health_check.py` (lines 27-31):
```python
TEST_URLS = {
    "ticketmaster": "https://www.ticketmaster.com/your-event",
    "stubhub": "https://www.stubhub.com/your-event",
    "viagogo": "https://www.viagogo.com/your-event",
}
```

2. Push to GitHub - the workflow (`.github/workflows/health-check.yml`) runs automatically:
   - Daily at 9 AM UTC
   - Manual trigger available in Actions tab
   - Downloads health check reports as artifacts
   - Workflow fails (red X) if any scraper fails

3. View results in GitHub:
   - Go to **Actions** tab
   - Click on latest "Daily Scraper Health Check" run
   - See pass/fail status
   - Download JSON report artifact

## Gmail Setup

For Gmail, you need to use an App Password:

1. Enable 2-factor authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password in `config/settings.yaml`

## Project Structure

```
tickets/
├── config/                      # Configuration files
│   ├── alerts.yaml.example     # Alert definitions template
│   └── settings.yaml.example   # App settings template
├── src/                        # Source code
│   ├── models.py              # Database models
│   ├── alert_manager.py       # Alert processing logic
│   ├── notifier.py            # Email notifications
│   ├── scheduler.py           # Periodic scheduling
│   ├── config.py              # Configuration loader
│   ├── health_check.py        # Scraper health validation
│   ├── scrapers/              # Web scrapers
│   │   ├── base.py           # Base scraper class
│   │   ├── ticketmaster.py   # Ticketmaster scraper
│   │   ├── stubhub.py        # StubHub scraper
│   │   └── viagogo.py        # Viagogo scraper
│   └── dashboard/             # Web dashboard
│       ├── app.py            # Flask application
│       └── templates/        # HTML templates
├── tests/                     # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_models.py        # Model tests
│   ├── test_scrapers.py      # Scraper tests
│   ├── test_alert_manager.py # Alert manager tests
│   └── test_notifier.py      # Notifier tests
├── data/                      # Runtime data (git-ignored)
│   ├── tickets.db            # SQLite database
│   ├── ticket_scraper.log    # Application logs
│   ├── health_check*.json    # Health check reports
│   └── errors/               # Debug screenshots/HTML
├── .github/workflows/         # GitHub Actions
│   └── health-check.yml      # Daily health check workflow
├── main.py                    # Application entry point
├── run_health_check.py        # Health check script
└── pyproject.toml            # Project dependencies
```

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

## Testing

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py

# Run specific test class
uv run pytest tests/test_scrapers.py::TestTicketmasterScraper
```

All 32 tests should pass:
- 11 alert manager tests (notification logic, processing)
- 7 model tests (database operations)
- 5 notifier tests (email sending)
- 9 scraper tests (web scraping)

## Health Checks

The health check system validates scrapers daily via GitHub Actions to catch issues early.

### How It Works

1. GitHub Actions runs health check daily at 9 AM UTC
2. Tests each scraper (Ticketmaster, StubHub, Viagogo) with real event URLs
3. Verifies prices are extracted correctly
4. Measures response times
5. Saves detailed JSON report as downloadable artifact
6. Workflow passes (✅) or fails (❌) based on results

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

### Running Health Checks

**Automated (GitHub Actions):**
- Runs automatically daily at 9 AM UTC
- View results: GitHub → **Actions** tab → "Daily Scraper Health Check"
- Download reports from workflow artifacts
- Workflow badge shows current status

**Manual (GitHub):**
- Go to **Actions** tab
- Click "Daily Scraper Health Check"
- Click "Run workflow" button → Run workflow
- Watch execution in real-time

**Manual (Local):**
```bash
# Run health check locally
uv run python run_health_check.py

# Custom timeout (in milliseconds)
uv run python run_health_check.py --timeout 60000

# Don't save report
uv run python run_health_check.py --no-save-report
```

### Viewing Results

**GitHub UI:**
- ✅ Green checkmark = All scrapers passed
- ❌ Red X = One or more scrapers failed
- Click workflow run for details
- Download `health-check-report-*.json` artifact

**Local report:**
```bash
# View latest report (formatted)
cat data/health_check_report.json | python -m json.tool

# Check success rate
cat data/health_check_report.json | python -c "
import json, sys
r = json.load(sys.stdin)
print(f'Success: {r[\"summary\"][\"success_rate\"]}%')
"
```

### Customizing Schedule

Edit `.github/workflows/health-check.yml`:

```yaml
# Twice daily (9 AM and 9 PM UTC)
schedule:
  - cron: '0 9,21 * * *'

# Every 6 hours
schedule:
  - cron: '0 */6 * * *'

# Weekdays only at 8 AM UTC
schedule:
  - cron: '0 8 * * 1-5'
```

### Troubleshooting Health Checks

**Workflow failing:**

1. Click on failed workflow run in GitHub Actions
2. View logs to see which scraper failed
3. Download artifact to see full error details
4. Common fixes:
   - Update test URLs if events expired
   - Check if website structure changed
   - Increase timeout in workflow file

**Running locally to debug:**
```bash
# Run with verbose output
uv run python run_health_check.py

# Test specific URL directly
uv run python -c "
from src.scrapers.stubhub import StubHubScraper
scraper = StubHubScraper(headless=False)
with scraper:
    result = scraper.scrape('YOUR_URL')
    print(result)
"
```

**Playwright issues in GitHub Actions:**
- The workflow installs Chromium with `--with-deps`
- If issues persist, check GitHub Actions logs
- May need to update Playwright version in `pyproject.toml`

## Troubleshooting

### Playwright detected as bot
- Set `headless: false` in settings.yaml to debug
- Add delays between actions
- Consider using residential proxies for production

### Selectors not finding elements
- Websites frequently change their HTML structure
- Use `headless: false` to inspect the page
- Update selectors in scraper files as needed
- Use Playwright inspector: `uv run playwright codegen <url>`

### Gmail blocking SMTP
- Ensure you're using an App Password, not your regular password
- Check that 2FA is enabled on your account
- Verify SMTP settings are correct

### Database locked errors
- Ensure only one instance of the application is running
- Check file permissions on data/ directory

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
