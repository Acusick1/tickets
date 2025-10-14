"""Email notification module for price alerts."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notifier for sending price alert notifications."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
    ):
        """Initialize the email notifier.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Email address to send from
            sender_password: Password or app password for sender email
            recipient_email: Email address to send notifications to
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_notification(
        self,
        alert_name: str,
        current_price: float,
        target_price: float,
        url: str,
        trigger_reason: str,
        previous_price: Optional[float] = None,
    ) -> bool:
        """Send a price drop notification email.

        Args:
            alert_name: Name of the alert
            current_price: Current ticket price
            target_price: Target price threshold
            url: URL to the event
            trigger_reason: Reason for notification (first_time, price_drop)
            previous_price: Previous price (for price drop notifications)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Price Alert: {alert_name}"
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email

            # Create email body
            if trigger_reason == "first_time":
                text_body = f"""
Price Alert: {alert_name}

The ticket price has dropped below your target!

Current Price: ${current_price:.2f}
Target Price: ${target_price:.2f}
Savings: ${target_price - current_price:.2f}

Event URL: {url}

This is the first time the price has been below your target.
"""
                html_body = f"""
<html>
  <body>
    <h2>Price Alert: {alert_name}</h2>
    <p>The ticket price has dropped below your target!</p>
    <table border="1" cellpadding="10" style="border-collapse: collapse;">
      <tr>
        <td><strong>Current Price:</strong></td>
        <td style="color: green; font-size: 18px;">${current_price:.2f}</td>
      </tr>
      <tr>
        <td><strong>Target Price:</strong></td>
        <td>${target_price:.2f}</td>
      </tr>
      <tr>
        <td><strong>Savings:</strong></td>
        <td style="color: green;">${target_price - current_price:.2f}</td>
      </tr>
    </table>
    <p><a href="{url}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; margin-top: 10px;">View Event</a></p>
    <p style="color: gray; font-size: 12px;">This is the first time the price has been below your target.</p>
  </body>
</html>
"""
            else:  # price_drop
                price_drop = previous_price - current_price if previous_price else 0
                prev_price_display = previous_price if previous_price else 0
                text_body = f"""
Price Alert: {alert_name}

The ticket price has dropped further!

Current Price: ${current_price:.2f}
Previous Price: ${prev_price_display:.2f}
Price Drop: ${price_drop:.2f}
Target Price: ${target_price:.2f}

Event URL: {url}

The price continues to fall. Act now!
"""
                html_body = f"""
<html>
  <body>
    <h2>Price Alert: {alert_name}</h2>
    <p>The ticket price has dropped further!</p>
    <table border="1" cellpadding="10" style="border-collapse: collapse;">
      <tr>
        <td><strong>Current Price:</strong></td>
        <td style="color: green; font-size: 18px;">${current_price:.2f}</td>
      </tr>
      <tr>
        <td><strong>Previous Price:</strong></td>
        <td style="text-decoration: line-through;">${prev_price_display:.2f}</td>
      </tr>
      <tr>
        <td><strong>Price Drop:</strong></td>
        <td style="color: green; font-weight: bold;">${price_drop:.2f}</td>
      </tr>
      <tr>
        <td><strong>Target Price:</strong></td>
        <td>${target_price:.2f}</td>
      </tr>
    </table>
    <p><a href="{url}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-align: center; text-decoration: none; display: inline-block; margin-top: 10px;">View Event</a></p>
    <p style="color: red; font-weight: bold;">The price continues to fall. Act now!</p>
  </body>
</html>
"""

            # Attach parts
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            msg.attach(part1)
            msg.attach(part2)

            # Send email
            logger.info(f"Sending notification email to {self.recipient_email}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(
                f"Notification sent successfully for {alert_name} (${current_price:.2f})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send notification email: {e}", exc_info=True)
            return False

    def test_connection(self) -> bool:
        """Test SMTP connection and credentials.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing SMTP connection to {self.smtp_host}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}", exc_info=True)
            return False
