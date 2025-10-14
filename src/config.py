"""Configuration loader for alerts and settings."""
import logging
from pathlib import Path
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)


def load_settings(config_path: str = "config/settings.yaml") -> Dict:
    """Load application settings from YAML file.

    Args:
        config_path: Path to settings YAML file

    Returns:
        Dictionary with settings
    """
    path = Path(config_path)
    if not path.exists():
        logger.error(f"Settings file not found: {config_path}")
        raise FileNotFoundError(f"Settings file not found: {config_path}")

    with open(path, "r") as f:
        settings = yaml.safe_load(f)

    logger.info(f"Loaded settings from {config_path}")
    return settings


def load_alerts(config_path: str = "config/alerts.yaml") -> List[Dict]:
    """Load alert definitions from YAML file.

    Args:
        config_path: Path to alerts YAML file

    Returns:
        List of alert dictionaries
    """
    path = Path(config_path)
    if not path.exists():
        logger.error(f"Alerts file not found: {config_path}")
        raise FileNotFoundError(f"Alerts file not found: {config_path}")

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    alerts = data.get("alerts", [])
    logger.info(f"Loaded {len(alerts)} alerts from {config_path}")
    return alerts


def sync_alerts_to_db(alerts_config: List[Dict], db_session):
    """Sync alert configurations to database.

    This will create new alerts and update existing ones based on name.

    Args:
        alerts_config: List of alert dictionaries from config
        db_session: Database session
    """
    from .models import Alert

    logger.info(f"Syncing {len(alerts_config)} alerts to database...")

    for alert_data in alerts_config:
        name = alert_data.get("name")
        if not name:
            logger.warning(f"Alert missing name, skipping: {alert_data}")
            continue

        # Check if alert exists
        existing = db_session.query(Alert).filter(Alert.name == name).first()

        if existing:
            # Update existing alert
            existing.source = alert_data.get("source", existing.source)
            existing.source_url = alert_data.get("url", existing.source_url)
            existing.target_price = alert_data.get("target_price", existing.target_price)
            existing.is_active = alert_data.get("active", existing.is_active)
            logger.info(f"Updated alert: {name}")
        else:
            # Create new alert
            new_alert = Alert(
                name=name,
                source=alert_data.get("source"),
                source_url=alert_data.get("url"),
                target_price=alert_data.get("target_price"),
                is_active=alert_data.get("active", True),
            )
            db_session.add(new_alert)
            logger.info(f"Created new alert: {name}")

    db_session.commit()
    logger.info("Alert sync completed")
