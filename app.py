import os
import json
import datetime
from flask import Flask, render_template_string, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

# Email settings via environment variables
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
            body { font-family: Arial; padding: 20px; }
            input, textarea, select { width: 100%; padding: 10px; margin: 5px 0; }
            button { padding: 15px; background: #007BFF; color: white; border: none; width: 100%; }
        </style>
    </head>
    <body>
        <h2>Opdrachtbon formulier</h2>
        <p><b>Datum & tijd:</b> {{now}}</p>
        <form action="/submit" method="post">
            <label>Klantnaam</label><input type="text" name="klantnaam" required>
            <label>Kenteken</label><input type="text" name="kenteken" required>
            <label>IMEI nummer</label><input type="text" name="imei">
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
    </body>
    </html>
    """
    return render_template_string(html, now=now)


@app.route("/submit", methods=["POST"])
def submit():
    klantnaam = request.form.get("klantnaam")
    kenteken = request.form.get("kenteken")
    imei = request.form.get("imei")
    werkzaamheden = request.form.get("werkzaamheden")
    opmerkingen = request.form.get("opmerkingen")
    klantemail = request.form.get("klantemail")

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    week_total, year_total, overall_total = update_counters()

    pdf_file = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4

    # Datum bovenaan
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height-2*cm, f"Datum: {now}")

    # Formulier gegevens
    c.setFont("Helvetica", 11)
    c.drawString(2*cm, height-3*cm, f"Klantnaam: {klantnaam}")
    c.drawString(2*cm, height-4*cm, f"Kenteken: {kenteken}")
    c.drawString(2*cm, height-5*cm, f"IMEI: {imei}")
    c.drawString(2*cm, height-6*cm, f"Werkzaamheden: {werkzaamheden}")
    c.drawString(2*cm, height-7*cm, f"Opmerkingen: {opmerkingen}")

    # Counters onderaan in grijs
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(2*cm, 1.5*cm,
                 f"Week totaal: {week_total} | Jaar totaal: {year_total} | Overall totaal: {overall_total}")

    c.save()

    # Email versturen
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
