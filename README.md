# IC-North Automotive Opdrachtbon

Dit project bevat een Flask-app die opdrachtbonnen registreert.

## Functies
- Formulier met klantnaam, kenteken, IMEI, werkzaamheden, opmerkingen en 3 foto’s
- Automatische datum/tijd in **Europe/Amsterdam**
- Week / Jaar / Overall tellers
- PDF generatie met gegevens en foto’s
- Automatische verzending per e-mail

## Deploy
1. Push deze repo naar GitHub
2. Koppel Render en klik **Deploy latest commit**
3. Stel env vars in op Render:
   - `SENDER_EMAIL`
   - `RECEIVER_EMAIL`
   - `PASSWORD` (App Password van Gmail)
