
# IC-North Automotive — complete patch

Bestanden in deze zip:
- `app.py` — formulier, RDW, PDF, mail via env vars, + `/healthz`, `/debug/send-test`, `/debug/env`
- `mailer.py` — SMTP helper (STARTTLS/SSL)
- `Procfile` — gunicorn startcommand
- `runtime.txt` — Python runtime (optioneel)

## Deploy-stappen
1. Upload/overschrijf deze 4 bestanden in de **root** van je GitHub repo.
2. Op Render: **Manual Deploy → Clear cache & deploy**.
3. Test: `/healthz` → ok, `/debug/send-test` → mail verstuurd.

## Benodigde Environment Variables (Render → Environment)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=icnorthautomotive@gmail.com
SMTP_PASSWORD=<Gmail App Password (16 chars)>
SMTP_STARTTLS=1
SMTP_USE_SSL=0
SENDER_EMAIL=icnorthautomotive@gmail.com
RECEIVER_EMAIL=icnorthautomotive@gmail.com
