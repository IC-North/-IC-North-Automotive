# IC-North Automotive — Complete Render patch

Bevat:
- `mailer.py` (SMTP mailer)
- `Procfile` (gunicorn op $PORT)
- `runtime.txt` (Python 3.11.9)
- Patch voor `app.py` met `/healthz` en `/debug/send-test` en mailer-import

## Deploy
1) Vervang/voeg deze bestanden in je repo.
2) Render → Manual Deploy → Clear cache & deploy.
3) Test `/debug/send-test`.

## Environment (Render)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=icnorthautomotive@gmail.com
SMTP_PASSWORD=<App Password>
SMTP_STARTTLS=1
SMTP_USE_SSL=0
SENDER_EMAIL=icnorthautomotive@gmail.com
RECEIVER_EMAIL=icnorthautomotive@gmail.com