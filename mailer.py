
import os
import smtplib
from email.message import EmailMessage
from typing import Optional, Iterable, Tuple

class MailConfigError(Exception):
    pass

def _bool_env(name: str, default: bool=False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1","true","yes","y","on"}

def build_message(subject: str, body_text: str, sender: str, recipient: str,
                  attachments: Optional[Iterable[Tuple[bytes, str, str]]] = None) -> EmailMessage:
    """
    attachments: iterable of tuples (content_bytes, filename, mime_type)
    mime_type like 'application/pdf' or 'image/png'
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content(body_text)
    if attachments:
        for content, filename, mime in attachments:
            maintype, _, subtype = mime.partition('/')
            if not subtype:
                maintype, subtype = 'application', 'octet-stream'
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    return msg

def send_email(msg: EmailMessage) -> str:
    """Send an EmailMessage using SMTP_* env vars.
    Returns a short status string for logging. Raises MailConfigError on missing config.
    Environment variables:
      - SMTP_HOST (required)
      - SMTP_PORT (optional; default 587 for STARTTLS, or 465 for SSL if SMTP_USE_SSL=1)
      - SMTP_USER (optional but recommended)
      - SMTP_PASSWORD (optional but required if server needs auth)
      - SMTP_USE_SSL (bool, default False) : connect via SMTP_SSL on port 465
      - SMTP_STARTTLS (bool, default True) : upgrade with starttls() after EHLO (when not using SSL)
      - SMTP_TIMEOUT (seconds; default 20)
    """
    host = os.getenv('SMTP_HOST')
    if not host:
        raise MailConfigError("SMTP_HOST is not set")
    use_ssl = _bool_env('SMTP_USE_SSL', False)
    starttls = _bool_env('SMTP_STARTTLS', True)
    timeout = float(os.getenv('SMTP_TIMEOUT', '20'))
    port = int(os.getenv('SMTP_PORT') or (465 if use_ssl else 587))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')

    if use_ssl:
        server = smtplib.SMTP_SSL(host=host, port=port, timeout=timeout)
    else:
        server = smtplib.SMTP(host=host, port=port, timeout=timeout)
    try:
        server.ehlo()
        if not use_ssl and starttls:
            server.starttls()
            server.ehlo()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return f"sent via {host}:{port}{' (SSL)' if use_ssl else ''}"
