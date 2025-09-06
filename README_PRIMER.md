# IC‑North Automotive — iOS permission-primer scanner

- Vraagt expliciet eerst camera-toestemming met `getUserMedia()`
- Leest daarna beschikbare camera’s, kiest achtercamera, start html5-qrcode
- Toont fouten in het scanvenster (rood) als iets misgaat

Mail-config blijft ongewijzigd (ENV).

Deploy: upload app.py, mailer.py, Procfile, runtime.txt → Render manual deploy (clear cache).
