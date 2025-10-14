"""Flask dashboard for viewing alerts and price history."""
import json
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, jsonify
from sqlalchemy import func

from src.models import Alert, PriceRecord, NotificationLog, get_session

app = Flask(__name__)


@app.route("/")
def index():
    """Dashboard home page."""
    db_session = get_session()

    try:
        # Get all alerts with statistics
        alerts = db_session.query(Alert).all()

        alert_stats = []
        for alert in alerts:
            # Get latest price
            latest_price = (
                db_session.query(PriceRecord)
                .filter(PriceRecord.alert_id == alert.id)
                .order_by(PriceRecord.timestamp.desc())
                .first()
            )

            # Get notification count
            notification_count = (
                db_session.query(func.count(NotificationLog.id))
                .filter(NotificationLog.alert_id == alert.id)
                .scalar()
            )

            alert_stats.append(
                {
                    "id": alert.id,
                    "name": alert.name,
                    "source": alert.source,
                    "target_price": alert.target_price,
                    "latest_price": latest_price.price if latest_price else None,
                    "latest_availability": (
                        latest_price.availability if latest_price else "unknown"
                    ),
                    "last_checked": (
                        alert.last_checked.strftime("%Y-%m-%d %H:%M:%S")
                        if alert.last_checked
                        else "Never"
                    ),
                    "is_active": alert.is_active,
                    "notification_count": notification_count,
                }
            )

        return render_template("dashboard.html", alerts=alert_stats)

    finally:
        db_session.close()


@app.route("/api/price-history/<int:alert_id>")
def price_history(alert_id):
    """Get price history for an alert."""
    db_session = get_session()

    try:
        # Get price records for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        records = (
            db_session.query(PriceRecord)
            .filter(
                PriceRecord.alert_id == alert_id,
                PriceRecord.timestamp >= thirty_days_ago,
            )
            .order_by(PriceRecord.timestamp.asc())
            .all()
        )

        # Get alert info
        alert = db_session.query(Alert).filter(Alert.id == alert_id).first()

        data = {
            "alert_name": alert.name if alert else "Unknown",
            "target_price": alert.target_price if alert else 0,
            "prices": [
                {
                    "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "price": record.price,
                    "availability": record.availability,
                }
                for record in records
            ],
        }

        return jsonify(data)

    finally:
        db_session.close()


@app.route("/api/notifications/<int:alert_id>")
def notifications(alert_id):
    """Get notification history for an alert."""
    db_session = get_session()

    try:
        logs = (
            db_session.query(NotificationLog)
            .filter(NotificationLog.alert_id == alert_id)
            .order_by(NotificationLog.sent_at.desc())
            .limit(10)
            .all()
        )

        data = [
            {
                "sent_at": log.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                "trigger_reason": log.trigger_reason,
                "price": log.price,
            }
            for log in logs
        ]

        return jsonify(data)

    finally:
        db_session.close()


if __name__ == "__main__":
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)

    print("Starting dashboard on http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
