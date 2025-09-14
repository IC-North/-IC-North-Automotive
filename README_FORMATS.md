# IC‑North Automotive — scanner formats fallback

Fix: verwijdert harde afhankelijkheid van `Html5QrcodeSupportedFormats`.
- Als de enum beschikbaar is, wordt hij gebruikt.
- Zo niet, dan start de scanner zonder `formatsToSupport` (werkt in Safari).

Deploy: upload app.py, mailer.py, Procfile, runtime.txt → Render manual deploy (clear cache).


---

## 2025-09 Update
- Kenteken placeholder vervangen door `Bijv. AB-123-C`.
- RDW endpoint retourneert nu het kenteken in **officiële schrijfwijze** en de UI zet dit direct in het veld.
- Bij meerdere RDW-resultaten kiezen we de nieuwste `datum_eerste_toelating`.
- Server-side gebruikt `format_officieel_rdws()` bij submit als laatste stap.
