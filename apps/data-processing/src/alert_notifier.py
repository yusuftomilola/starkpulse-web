"""
Alert Notifier module - Sends notifications for detected anomalies
via multiple channels (Telegram, Webhooks).
"""

import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.anomaly_detector import AnomalyResult

logger = logging.getLogger(__name__)

class AlertNotifier:
    """
    Multichannel notification manager for system anomalies.
    Supports Telegram Bot API and generic JSON webhooks.
    """

    def __init__(self, min_severity: float = 0.5):
        """
        Initialize the notifier.
        Args:
            min_severity: Minimum severity score (0.0-1.0) to trigger alerts.
        """
        self.min_severity = min_severity
        # Telegram Config
        self.tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.tg_chat_id = os.getenv("TELEGRAM_CHANNEL_ID")
        
        # Webhook Config
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        
        # Status
        self.has_telegram = bool(self.tg_token and self.tg_chat_id)
        self.has_webhook = bool(self.webhook_url)
        
        if not (self.has_telegram or self.has_webhook):
            logger.warning("AlertNotifier initialized with no active channels. Alerts will only be logged.")

    def _send_telegram(self, message: str):
        """Send message via Telegram Bot API."""
        if not self.has_telegram:
            return
            
        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        payload = {
            "chat_id": self.tg_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    def _send_webhook(self, data: Dict[str, Any]):
        """Send JSON payload to generic webhook."""
        if not self.has_webhook:
            return
            
        try:
            response = requests.post(
                self.webhook_url, 
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Webhook alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Webhook alert: {e}")

    def format_anomaly_message(self, result: AnomalyResult) -> str:
        """Format AnomalyResult for Telegram (HTML)."""
        severity_emoji = "🔴" if result.severity_score > 0.8 else "🟠"
        
        return (
            f"🚨 <b>{result.metric_name.upper()} ANOMALY DETECTED</b> {severity_emoji}\n\n"
            f"<b>Severity:</b> {result.severity_score:.2f}\n"
            f"<b>Value:</b> {result.current_value:,.4f}\n"
            f"<b>Z-Score:</b> {result.z_score:.2f}\n"
            f"<b>Baseline Mean:</b> {result.baseline_mean:,.4f}\n"
            f"<b>Timestamp:</b> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"<i>#LumenPulse #Anomalies #Alert</i>"
        )

    def notify_anomaly(self, result: AnomalyResult):
        """Send notifications for a single anomaly if it meets severity threshold."""
        if not result.is_anomaly or result.severity_score < self.min_severity:
            return

        logger.info(f"Notifying anomaly: {result.metric_name} (severity={result.severity_score:.2f})")
        
        # 1. Telegram
        if self.has_telegram:
            msg = self.format_anomaly_message(result)
            self._send_telegram(msg)
            
        # 2. Webhook
        if self.has_webhook:
            self._send_webhook({
                "event": "anomaly_detected",
                "severity": "high" if result.severity_score > 0.8 else "medium",
                "data": result.to_dict()
            })

    def notify_batch(self, results: List[AnomalyResult]):
        """Filter and notify for a list of results."""
        for result in results:
            if result.is_anomaly:
                self.notify_anomaly(result)

# Singleton instance for easy import
notifier = AlertNotifier(
    min_severity=float(os.getenv("ALERT_MIN_SEVERITY", "0.5"))
)
