# IC‑North Automotive — scanner formats fallback

Fix: verwijdert harde afhankelijkheid van `Html5QrcodeSupportedFormats`.
- Als de enum beschikbaar is, wordt hij gebruikt.
- Zo niet, dan start de scanner zonder `formatsToSupport` (werkt in Safari).

Deploy: upload app.py, mailer.py, Procfile, runtime.txt → Render manual deploy (clear cache).
