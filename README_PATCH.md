# IC-North Automotive — Fix for newline import issue

Wat is er gefixt?
- De fout `SyntaxError: unexpected character after line continuation character` kwam doordat er letterlijk `\n` in de eerste regel van `app.py` stond.
- Deze patch vervangt dat door echte nieuwe regels, voegt een healthcheck en een testmail-route toe, en zet een correct `Procfile` en `runtime.txt`.

## Stappen
1) Vervang in je GitHub repo de volgende bestanden met de versies uit deze zip:
   - `app.py`
   - `mailer.py`
   - `Procfile`
   - `runtime.txt` (Render accepteert `3.11.9`)
2) In Render: **Manual Deploy → Clear cache & deploy**
3) Test: bezoek `/debug/send-test` en controleer je inbox.

## Benodigde env vars (Render → Environment)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=icnorthautomotive@gmail.com
SMTP_PASSWORD=<App Password>
SMTP_STARTTLS=1
SMTP_USE_SSL=0
SENDER_EMAIL=icnorthautomotive@gmail.com
RECEIVER_EMAIL=icnorthautomotive@gmail.com