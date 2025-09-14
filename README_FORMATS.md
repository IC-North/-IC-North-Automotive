# IC‑North Automotive — scanner formats fallback

Fix: verwijdert harde afhankelijkheid van `Html5QrcodeSupportedFormats`.
- Als de enum beschikbaar is, wordt hij gebruikt.
- Zo niet, dan start de scanner zonder `formatsToSupport` (werkt in Safari).

Deploy: upload app.py, mailer.py, Procfile, runtime.txt → Render manual deploy (clear cache).


---

## Fix3
- Patroonondersteuning aangevuld met **AAA-99-A** en **A-99-AAA** (o.a. voor kenteken zoals VGK33T → `VGK-33-T`).
