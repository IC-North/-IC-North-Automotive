# IC‑North Automotive – Opdrachtbon (Deploy Ready)

Deze repository is klaar voor deployment op **Render** (of Heroku-achtig).
De app genereert een **PDF opdrachtbon** en kan deze per e‑mail versturen.

## Snel starten (lokaal)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_ENV=production
export SMTP_PASSWORD="<gmail-app-wachtwoord>"
export RECEIVER_EMAIL="administratie@example.com"   # optioneel bcc
export MAIL_SUBJECT="Opdrachtbon – {klantnaam} – {kenteken}"
export MAIL_BODY="In de bijlage vind je de opdrachtbon (PDF)."
python app.py
```

Open: http://127.0.0.1:5000

> Tip: De afzender komt uit het formulier **Eigen e‑mail (afzender)** en moet overeenkomen met het mailbox‑account waar je met je app‑wachtwoord op inlogt.

## Render (of Heroku) deploy

1. Push deze map naar GitHub.
2. Maak een nieuwe **Web Service** in Render en selecteer je repo.
3. **Build Command**: *(leeg laten, Render installeert via `requirements.txt`)*
4. **Start Command**: wordt uit `Procfile` gehaald: `web: gunicorn app:app`
5. **Environment Variables** zetten:
   - `SMTP_PASSWORD` = je Gmail **app‑wachtwoord** (vereist bij 2FA)
   - `RECEIVER_EMAIL` = administratie/bcc (optioneel)
   - `SMTP_HOST` = `smtp.gmail.com` (optioneel, standaard)
   - `SMTP_PORT` = `587` (optioneel, standaard)
   - `MAIL_SUBJECT` = bijvoorbeeld `Opdrachtbon – {klantnaam} – {kenteken}`
   - `MAIL_BODY` = bijvoorbeeld `In de bijlage vind je de opdrachtbon (PDF).`
6. Eventueel `TZ` zetten op `Europe/Amsterdam` als je system‑timezone wilt afdwingen.

> Let op: Als Render klaagt over de Python‑versie uit `runtime.txt`, zet daar een versie neer die door Render wordt ondersteund (bijv. `python-3.11.9`).

## Bekende valkuilen

- **Internal Server Error (500)** bij `/submit`: meestal komt dit door e‑mailconfig (afzender/wachtwoord) of een ontbrekende `filename`. In deze build is dat gefixt.
- Gmail vereist een **app‑wachtwoord**. Gewone account‑wachtwoorden werken niet met SMTP + TLS.
- RDW API kan rate‑limiten; probeer later opnieuw of gebruik een `X-App-Token` (niet vereist).

## Omgevingsvariabelen (overzicht)

| Variabele      | Default               | Uitleg |
|----------------|-----------------------|--------|
| `SMTP_HOST`    | `smtp.gmail.com`      | SMTP server |
| `SMTP_PORT`    | `587`                 | SMTP poort (TLS) |
| `SMTP_PASSWORD`| *(geen)*              | Gmail app‑wachtwoord |
| `RECEIVER_EMAIL` | *(geen)*            | BCC/administratie (optioneel) |
| `MAIL_SUBJECT` | `Opdrachtbon – {klantnaam} – {kenteken}` | Onderwerp, placeholders toegestaan |
| `MAIL_BODY`    | `In de bijlage vind je de opdrachtbon (PDF).` | Tekst van de mail |
| `TZ`           | *(none)*              | Optioneel, bv. `Europe/Amsterdam` |

---

_Laat het weten als ik het onderwerp/body **hardcoded exact** moet zetten in plaats van via env. Dan pas ik `app.py` direct aan._
