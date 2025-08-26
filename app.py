import os
import datetime
import requests
from flask import Flask, render_template_string, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

app = Flask(__name__)

# RDW API base
RDW_API = "https://opendata.rdw.nl/api/records/1.0/search/"

def get_car_info(kenteken):
    try:
        params = {
            "dataset": "m9d7-ebf2",
            "q": kenteken.replace("-", "").upper(),
        }
        r = requests.get(RDW_API, params=params, timeout=5)
        data = r.json()
        if data.get("records"):
            fields = data["records"][0]["fields"]
            merk = fields.get("merk", "Onbekend")
            handelsbenaming = fields.get("handelsbenaming", "Onbekend")
            bouwjaar = fields.get("datum_eerste_toelating", "Onbekend")[:4]
            return merk, handelsbenaming, bouwjaar
    except Exception:
        pass
    return "Onbekend", "Onbekend", "Onbekend"

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = '''
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Opdrachtbon</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background:#f5f7fa; }
            input, textarea, select { width: 100%; padding: 10px; margin: 8px 0; border:1px solid #ccc; border-radius:6px; }
            button { padding: 15px; background: #004080; color: white; border: none; width: 100%; border-radius:6px; font-size:16px; }
            h2 { color:#004080; }
        </style>
    </head>
    <body>
        <h2>Opdrachtbon formulier</h2>
        <p><b>Datum & tijd:</b> {{now}}</p>
        <form action="/submit" method="post">
            <label>Klantnaam</label><input type="text" name="klantnaam" required>
            <label>Kenteken</label><input type="text" name="kenteken" required placeholder="XX-999-X">
            <label>IMEI nummer (scan/voer in)</label><input type="text" name="imei" placeholder="scan of vul in">
            <label>Chassisnummer (VIN)</label><input type="text" name="vin" maxlength="17" minlength="17" required placeholder="17 tekens">
            <label>Werkzaamheden</label>
            <select name="werkzaamheden">
                <option>Inbouw</option>
                <option>Ombouw</option>
                <option>Overbouw</option>
                <option>Uitbouw</option>
                <option>Servicecall</option>
            </select>
            <label>Opmerkingen</label><textarea name="opmerkingen"></textarea>
            <button type="submit">Verstuur opdrachtbon</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(html, now=now)

@app.route("/submit", methods=["POST"])
def submit():
    klantnaam = request.form.get("klantnaam")
    kenteken = request.form.get("kenteken").upper()
    imei = request.form.get("imei")
    vin = request.form.get("vin")
    werkzaamheden = request.form.get("werkzaamheden")
    opmerkingen = request.form.get("opmerkingen")

    merk, handelsbenaming, bouwjaar = get_car_info(kenteken)

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf_file = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height-2*cm, f"Datum: {now}")

    c.setFont("Helvetica", 11)
    c.drawString(2*cm, height-3*cm, f"Klantnaam: {klantnaam}")
    c.drawString(2*cm, height-4*cm, f"Kenteken: {kenteken}")
    c.drawString(2*cm, height-5*cm, f"Merk/Type/Bouwjaar: {merk} {handelsbenaming} {bouwjaar}")
    c.drawString(2*cm, height-6*cm, f"IMEI: {imei}")
    c.drawString(2*cm, height-7*cm, f"VIN: {vin}")
    c.drawString(2*cm, height-8*cm, f"Werkzaamheden: {werkzaamheden}")
    c.drawString(2*cm, height-9*cm, f"Opmerkingen: {opmerkingen}")

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(2*cm, 1.5*cm, "IC-North Automotive | Automatisch gegenereerde opdrachtbon")

    c.save()
    return send_file(pdf_file, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
