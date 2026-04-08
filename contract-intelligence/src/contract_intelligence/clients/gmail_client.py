import imaplib
import smtplib
import email as email_lib
from email.message import EmailMessage
from email.header import decode_header
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GmailClient:
    def __init__(self, user: str, app_password: str,
                 imap_host: str = "imap.gmail.com",
                 smtp_host: str = "smtp.gmail.com", smtp_port: int = 587):
        self.user = user
        self.app_password = app_password
        self.imap_host = imap_host
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def fetch_latest_quote_email(self) -> Optional[dict]:
        """Poll INBOX for unread emails with PDF attachments. Returns first match."""
        try:
            with imaplib.IMAP4_SSL(self.imap_host) as imap:
                imap.login(self.user, self.app_password)
                imap.select("INBOX")
                _, msg_ids = imap.search(None, "UNSEEN")
                for mid in reversed(msg_ids[0].split()):
                    _, data = imap.fetch(mid, "(RFC822)")
                    msg = email_lib.message_from_bytes(data[0][1])
                    pdf_data = self._extract_pdf(msg)
                    if pdf_data:
                        sender = msg.get("From", "")
                        subject = self._decode_header(msg.get("Subject", ""))
                        imap.store(mid, "+FLAGS", "\\Seen")
                        return {"sender": sender, "subject": subject, "pdf": pdf_data}
        except Exception as e:
            logger.error("IMAP error: %s", str(e))
        return None

    def _extract_pdf(self, msg) -> Optional[bytes]:
        for part in msg.walk():
            if part.get_content_type() == "application/pdf":
                return part.get_payload(decode=True)
            if part.get_filename() and part.get_filename().lower().endswith(".pdf"):
                return part.get_payload(decode=True)
        return None

    def _decode_header(self, value: str) -> str:
        parts = decode_header(value)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return " ".join(decoded)

    def send_email(self, to: list[str], subject: str, body: str,
                   attachment_path: Optional[Path] = None):
        """Send email with optional PDF attachment."""
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.set_content(body)

        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                                   filename=attachment_path.name)
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.user, self.app_password)
                smtp.send_message(msg)
            logger.info("Email sent to %s: %s", to, subject)
        except Exception as e:
            logger.error("SMTP error sending to %s: %s", to, str(e))
            raise

    def send_review_notification(self, revops_email: str, contract_id: str,
                                 review_url: str, risk_summary: str):
        body = f"""A contract requires your review.

Contract ID: {contract_id}
Risk Assessment: {risk_summary}

Review and approve or decline here:
{review_url}

This is an automated notification from contract-intelligence.
"""
        self.send_email(
            to=[revops_email],
            subject=f"[ACTION REQUIRED] Contract Review — {contract_id}",
            body=body,
        )
