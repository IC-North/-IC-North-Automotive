
import os, smtplib
from email.message import EmailMessage
from typing import Optional, Iterable, Tuple

class MailConfigError(Exception): pass

def _bool_env(name: str, default: bool=False) -> bool:
  v = os.getenv(name); 
  if v is None: return default
  return v.strip().lower() in {"1","true","yes","y","on"}

def build_message(subject: str, body_text: str, sender: str, recipient: str,
                  attachments: Optional[Iterable[Tuple[bytes, str, str]]] = None) -> EmailMessage:
  msg = EmailMessage(); msg['Subject']=subject; msg['From']=sender; msg['To']=recipient; msg.set_content(body_text)
  if attachments:
    for content, filename, mime in attachments:
      maintype, _, subtype = mime.partition('/')
      if not subtype: maintype, subtype = 'application','octet-stream'
      msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
  return msg

def send_email(msg: EmailMessage) -> str:
  host = os.getenv('SMTP_HOST')
  if not host: raise MailConfigError("SMTP_HOST is not set")
  use_ssl = _bool_env('SMTP_USE_SSL', False); starttls = _bool_env('SMTP_STARTTLS', True)
  timeout = float(os.getenv('SMTP_TIMEOUT', '20')); port = int(os.getenv('SMTP_PORT') or (465 if use_ssl else 587))
  user = os.getenv('SMTP_USER'); password = os.getenv('SMTP_PASSWORD')
  server = smtplib.SMTP_SSL(host=host, port=port, timeout=timeout) if use_ssl else smtplib.SMTP(host=host, port=port, timeout=timeout)
  try:
    server.ehlo(); 
    if not use_ssl and starttls: server.starttls(); server.ehlo()
    if user and password: server.login(user, password)
    server.send_message(msg)
  finally:
    try: server.quit()
    except Exception: pass
  return f"sent via {host}:{port}{' (SSL)' if use_ssl else ''}"
