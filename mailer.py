# mailer.py
import os
import base64
import json
import requests
from email.message import EmailMessage
from typing import Optional, Iterable, Tuple, List

class MailConfigError(Exception):
    pass

def build_message(
    subject: str,
    body_text: str,
    sender: str,
    recipient: str,
    attachments: Optional[Iterable[Tuple[bytes, str, str]]] = None
) -> EmailMessage:
    """
    Bouwt een EmailMessage object (zelfde interface als voorheen).
    attachments: iterable van (content_bytes, filename, mime_type)
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content(body_text)

    if attachments:
        for content_bytes, filename, mime in attachments:
            maintype, subtype = (mime.split('/', 1) + ['octet-stream'])[:2]
            msg.add_attachment(content_bytes, maintype=maintype, subtype=subtype, filename=filename)

    return msg

def _extract_attachments(msg: EmailMessage) -> List[Tuple[bytes, str, str]]:
    """Haal (bytes, filename, mime) uit EmailMessage bijlagen."""
    atts: List[Tuple[bytes, str, str]] = []
    for part in msg.iter_attachments():
        payload = part.get_payload(decode=True)
        filename = part.get_filename() or "attachment.bin"
        mime = part.get_content_type()
        atts.append((payload, filename, mime))
    return atts

def _split_emails(s: str) -> List[str]:
    if not s:
        return []
    # ondersteunt komma of puntkomma
    parts = [p.strip() for p in s.replace(';', ',').split(',') if p.strip()]
    # simpele validatie
    return [p for p in parts if '@' in p]

def send_email(msg: EmailMessage) -> str:
    """
    Verstuur e-mail via Twilio SendGrid REST API.
    Vereist:
      - SENDGRID_API_KEY (env)
      - 'From' moet geverifieerd zijn in SendGrid (Single Sender of Domain Auth)
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        raise MailConfigError("SENDGRID_API_KEY is not set")

    from_email = msg.get('From')
    to_emails = _split_emails(msg.get('To', ''))
    if not from_email:
        raise MailConfigError("From address missing")
    if not to_emails:
        raise MailConfigError("Recipient(s) missing")

    # Bouw payload
    body_part = msg.get_body(preferencelist=('plain', 'html'))
    body_text = body_part.get_content() if body_part else ""

    data = {
        "personalizations": [{
            "to": [{"email": e} for e in to_emails],
            "subject": msg.get('Subject', '')
        }],
        "from": {"email": from_email},
        "content": [{
            "type": "text/plain",
            "value": body_text
        }],
    }

    # Reply-To (optioneel)
    reply_to = msg.get('Reply-To')
    if reply_to:
        data["reply_to"] = {"email": reply_to}

    # Bijlagen
    attachments = _extract_attachments(msg
