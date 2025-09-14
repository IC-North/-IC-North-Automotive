# IC‑North Automotive — scanner formats fallback

Fix: verwijdert harde afhankelijkheid van `Html5QrcodeSupportedFormats`.
- Als de enum beschikbaar is, wordt hij gebruikt.
- Zo niet, dan start de scanner zonder `formatsToSupport` (werkt in Safari).

Deploy: upload app.py, mailer.py, Procfile, runtime.txt → Render manual deploy (clear cache).


---

## Fix2
- Live formattering gebruikt nu patronen op basis van letters/cijfers (niet alleen lengte).
- RDW-respons bevat `kenteken` met streepjes; UI zet dit direct.
- `/format_kenteken` geeft nu dezelfde officiële formatter terug.
