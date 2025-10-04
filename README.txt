
IC-North Platform Starter

Deploy op Render:
1) Nieuwe Web Service → upload ZIP.
2) Zet Environment Variables:
   - DATABASE_URL (Render PostgreSQL of externe) — voorbeeld: postgresql://USER:PASS@HOST:5432/DB
   - SENDGRID_API_KEY
   - SENDER_EMAIL (geverifieerd in SendGrid)
   - RECEIVER_EMAIL (optioneel; meerdere gescheiden door comma of puntkomma)
3) Manual Deploy.
4) Na eerste start: open /admin om data te bekijken.
Test mail: /mail_test?to=je@adres.nl
