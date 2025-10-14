"""Tests for email notifier."""
import pytest

from src.notifier import EmailNotifier


class TestNotifier:
    """Tests for EmailNotifier class."""

    def test_initialization(self):
        """Test notifier initialization."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="password",
            recipient_email="recipient@test.com",
        )

        assert notifier.smtp_host == "smtp.test.com"
        assert notifier.smtp_port == 587
        assert notifier.sender_email == "sender@test.com"
        assert notifier.recipient_email == "recipient@test.com"

    def test_send_notification_first_time(self, mock_smtp):
        """Test sending first-time notification."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="password",
            recipient_email="recipient@test.com",
        )

        result = notifier.send_notification(
            alert_name="Test Event",
            current_price=95.00,
            target_price=100.00,
            url="https://test.com",
            trigger_reason="first_time",
        )

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("sender@test.com", "password")
        mock_smtp.send_message.assert_called_once()

    def test_send_notification_price_drop(self, mock_smtp):
        """Test sending price drop notification."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="password",
            recipient_email="recipient@test.com",
        )

        result = notifier.send_notification(
            alert_name="Test Event",
            current_price=85.00,
            target_price=100.00,
            url="https://test.com",
            trigger_reason="price_drop",
            previous_price=95.00,
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_notification_failure(self, mocker):
        """Test notification failure handling."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="password",
            recipient_email="recipient@test.com",
        )

        # Mock SMTP to raise an exception
        mocker.patch(
            "smtplib.SMTP", side_effect=Exception("SMTP connection failed")
        )

        result = notifier.send_notification(
            alert_name="Test Event",
            current_price=95.00,
            target_price=100.00,
            url="https://test.com",
            trigger_reason="first_time",
        )

        assert result is False

    def test_test_connection_success(self, mock_smtp):
        """Test successful SMTP connection test."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="password",
            recipient_email="recipient@test.com",
        )

        result = notifier.test_connection()

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()

    def test_test_connection_failure(self, mocker):
        """Test failed SMTP connection test."""
        notifier = EmailNotifier(
            smtp_host="smtp.test.com",
            smtp_port=587,
            sender_email="sender@test.com",
            sender_password="bad_password",
            recipient_email="recipient@test.com",
        )

        # Mock SMTP to raise an exception
        mocker.patch(
            "smtplib.SMTP", side_effect=Exception("Authentication failed")
        )

        result = notifier.test_connection()

        assert result is False
