# IC‑North Opdrachtbon (Render-ready)

- RDW-koppeling: automatisch **Merk/Type/Bouwjaar** na invoer kenteken
- iPhone-ready **camera scanner**: IMEI & VIN scannen (barcode), QR via togglen
- PDF genereren en downloaden

## Deploy (Render)
1. Maak een nieuwe **Web Service** → Python → **Deploy from a folder/repo** of **ZIP**.
2. Upload deze map of de ZIP.
3. Render installeert: `flask, reportlab, gunicorn, requests`.
4. Start via `Procfile` → `gunicorn app:app`.

> iOS vereist **HTTPS** voor camera-toegang. Render is HTTPS, dus scannen werkt.

