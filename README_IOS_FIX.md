# IC‑North Automotive — iOS camera scanner FIX

Wat is aangepast:
- `#reader` heeft vaste hoogte (60vh) zodat video altijd zichtbaar is.
- `openScanner()`:
  - active input wordt geblurd + naar boven scrollen (iOS keyboard bug).
  - Eerst `getCameras()` → kiest achtercamera → dan pas `start()`.
  - Kleine delay (100ms) na openen overlay zodat iOS de layout kan renderen.
  - Torch-knop waar mogelijk, aspectRatio 16:9.
- Detectie en verwerking IMEI (14→15 met Luhn) en VIN (17, zonder I/O/Q).

Mail-setup blijft ongewijzigd en komt uit ENV.

## Deploy
1) Upload deze files naar repo-root (overschrijven mag): app.py, mailer.py, Procfile, runtime.txt
2) Render → Manual Deploy → Clear cache & deploy
3) Test op iPhone Safari: knop **Scan IMEI** of **Scan VIN** zou camera prompten en live beeld tonen.
