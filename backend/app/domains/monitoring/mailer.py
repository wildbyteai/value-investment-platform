"""E-mail delivery. SMTP settings come from the environment (VIP_SMTP_*); the sender
defaults to config/alerts-v1.json (admin@bytewatcher.xyz)."""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

from app.domains.monitoring.policy import policy, sender_address


class Mailer(Protocol):
    configured: bool

    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpMailer:
    def __init__(self, settings=None):
        from app.config import get_settings
        self.s = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.s.smtp_host)

    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg['From'] = formataddr((policy()['sender']['display_name'], sender_address()))
        msg['To'] = to
        msg['Subject'] = subject
        msg.set_content(body)
        context = ssl.create_default_context()
        if self.s.smtp_starttls:
            with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=30) as smtp:
                smtp.starttls(context=context)
                self._login(smtp)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP_SSL(self.s.smtp_host, self.s.smtp_port, timeout=30, context=context) as smtp:
                self._login(smtp)
                smtp.send_message(msg)

    def _login(self, smtp):
        if self.s.smtp_user:
            smtp.login(self.s.smtp_user, self.s.smtp_password.get_secret_value())
