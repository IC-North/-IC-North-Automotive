# IC‑North Automotive — PRODUCTION package

Dit pakket is klaar voor productie:
- `app.py` zonder debug-routes, met Reply-To en multiple admin ontvangers (komma of puntkomma gescheiden in `RECEIVER_EMAIL`).
- `mailer.py` voor SMTP (Gmail).
- `Procfile` en `runtime.txt` voor Render.

## Deploy
1) Upload/overschrijf **alle bestanden** in de root van je GitHub repo.
2) Render → Manual Deploy → **Clear cache & deploy**.
3) Test formulier en controleer je mailbox.

## Vereiste ENV (Render → Environment)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=icnorthautomotive@gmail.com
SMTP_PASSWORD=<Gmail App Password (16 chars)>
SMTP_STARTTLS=1
SMTP_USE_SSL=0
SENDER_EMAIL=icnorthautomotive@gmail.com
RECEIVER_EMAIL=icnorthautomotive@gmail.com   # of meerdere, gescheiden door , of ;

## Optioneel
- Wil je SSL i.p.v. STARTTLS? Zet:
  SMTP_USE_SSL=1, SMTP_STARTTLS=0, SMTP_PORT=465
