import os
import json
import datetime
import requests
from flask import Flask, render_template_string, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")
PASSWORD = os.environ.get("PASSWORD")

COUNTERS_FILE = "counters.json"

def load_counters():
    if os.path.exists(COUNTERS_FILE):
        with open(COUNTERS_FILE, "r") as f:
            return json.load(f)
    else:
        return {"week": {}, "year": {}, "overall": 0}

def save_counters(counters):
    with open(COUNTERS_FILE, "w") as f:
        json.dump(counters, f)

def update_counters():
    now = datetime.datetime.now()
    year = str(now.year)
    week = str(now.isocalendar()[1])
    counters = load_counters()
    counters["overall"] += 1
    if year not in counters["year"]:
        counters["year"][year] = 0
    counters["year"][year] += 1
    if week not in counters["week"]:
        counters["week"][week] = 0
    counters["week"][week] += 1
    save_counters(counters)
    return counters["week"][week], counters["year"][year], counters["overall"]

# RDW API call
def get_rdw_data(kenteken):
    try:
        url = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kenteken.replace('-','').upper()}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and len(r.json()) > 0:
            data = r.json()[0]
            merk = data.get("merk", "")
            handelsbenaming = data.get("handelsbenaming", "")
            bouwjaar = data.get("datum_eerste_toelating", "")
            if bouwjaar and len(bouwjaar) >= 4:
                bouwjaar = bouwjaar[:4]
            return {"merk": merk, "type": handelsbenaming, "bouwjaar": bouwjaar}
    except Exception as e:
        print("RDW error:", e)
    return {}

@app.route("/rdw/<kenteken>")
def rdw_lookup(kenteken):
    return jsonify(get_rdw_data(kenteken))

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = """
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Opdrachtbon</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f7fa; }
            h2 { color: #003366; }
            input, textarea, select { width: 100%; padding: 10px; margin: 5px 0; border-radius: 6px; border: 1px solid #ccc; }
            button { padding: 12px; background: #003366; color: white; border: none; width: 100%; border-radius: 6px; }
            .scanner-btn { background: #0066cc; margin-top: 5px; }
        </style>
    </head>
    <body>
        <h2>Opdrachtbon formulier</h2>
        <p><b>Datum & tijd:</b> {{now}}</p>
        <form action="/submit" method="post">
            <label>Klantnaam</label><input type="text" name="klantnaam" required>
            <label>Kenteken</label><input type="text" id="kenteken" name="kenteken" required onblur="formatKenteken()">
            <button type="button" onclick="checkRDW()">Zoek RDW gegevens</button>
            <label>Merk</label><input type="text" id="merk" name="merk" readonly>
            <label>Type</label><input type="text" id="type" name="type" readonly>
            <label>Bouwjaar</label><input type="text" id="bouwjaar" name="bouwjaar" readonly>

            <label>IMEI nummer</label>
            <input type="text" id="imei" name="imei">
            <button type="button" class="scanner-btn" onclick="startScanner('imei')">Scan IMEI</button>

            <label>Chassisnummer (VIN)</label>
            <input type="text" id="vin" name="vin" maxlength="17">
            <button type="button" class="scanner-btn" onclick="startScanner('vin')">Scan VIN</button>

            <label>Werkzaamheden</label>
            <select name="werkzaamheden">
                <option>Inbouw</option>
                <option>Ombouw</option>
                <option>Overbouw</option>
                <option>Uitbouw</option>
                <option>Servicecall</option>
            </select>
            <label>Opmerkingen</label><textarea name="opmerkingen"></textarea>
            <label>Klant email</label><input type="email" name="klantemail">
            <button type="submit">Verstuur opdrachtbon</button>
        </form>

        <!-- QR Scanner Lib -->
        <script src="https://unpkg.com/html5-qrcode"></script>
        <script>
            function formatKenteken() {
                let val = document.getElementById("kenteken").value.toUpperCase().replace(/[^A-Z0-9]/g, "");
                if(val.length == 6) {
                    val = val.replace(/(.{2})(.{2})(.{2})/, "$1-$2-$3");
                } else if(val.length == 7) {
                    val = val.replace(/(.{2})(.{3})(.{2})/, "$1-$2-$3");
                }
                document.getElementById("kenteken").value = val;
            }
            function checkRDW() {
                let kenteken = document.getElementById("kenteken").value;
                fetch("/rdw/" + kenteken).then(r => r.json()).then(d => {
                    document.getElementById("merk").value = d.merk || "";
                    document.getElementById("type").value = d.type || "";
                    document.getElementById("bouwjaar").value = d.bouwjaar || "";
                });
            }
            function startScanner(fieldId) {
                const html5QrCode = new Html5Qrcode("reader");
                html5QrCode.start(
                    { facingMode: "environment" },
                    { fps: 10, qrbox: 250 },
                    (decodedText) => {
                        document.getElementById(fieldId).value = decodedText;
                        html5QrCode.stop();
                        document.getElementById("reader").innerHTML = "";
                    }
                );
            }
        </script>
        <div id="reader" style="width:300px; margin-top:20px;"></div>
    </body>
    </html>
    """
    return render_template_string(html, now=now)

@app.route("/submit", methods=["POST"])
def submit():
    klantnaam = request.form.get("klantnaam")
    kenteken = request.form.get("kenteken")
    merk = request.form.get("merk")
    type_auto = request.form.get("type")
    bouwjaar = request.form.get("bouwjaar")
    imei = request.form.get("imei")
    vin = request.form.get("vin")
    werkzaamheden = request.form.get("werkzaamheden")
    opmerkingen = request.form.get("opmerkingen")
    klantemail = request.form.get("klantemail")

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    week_total, year_total, overall_total = update_counters()

    pdf_file = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height-2*cm, f"Datum: {now}")
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, height-3*cm, f"Klantnaam: {klantnaam}")
    c.drawString(2*cm, height-4*cm, f"KENTEKEN: {kenteken} ({merk} {type_auto}, {bouwjaar})")
    c.drawString(2*cm, height-5*cm, f"IMEI: {imei}")
    c.drawString(2*cm, height-6*cm, f"VIN: {vin}")
    c.drawString(2*cm, height-7*cm, f"Werkzaamheden: {werkzaamheden}")
    c.drawString(2*cm, height-8*cm, f"Opmerkingen: {opmerkingen}")

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(2*cm, 1.5*cm,
                 f"Week totaal: {week_total} | Jaar totaal: {year_total} | Overall totaal: {overall_total}")
    c.save()

    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = f"Opdrachtbon - {klantnaam}"
        body = MIMEText("Zie bijlage voor de opdrachtbon.", "plain")
        msg.attach(body)
        with open(pdf_file, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=pdf_file)
            msg.attach(attach)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL, klantemail], msg.as_string())
        return "Opdrachtbon verstuurd!"
    except Exception as e:
        return f"Fout bij verzenden e-mail: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
