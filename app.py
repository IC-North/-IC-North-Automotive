
import os
import io
import json
import datetime
import pytz
import requests
from flask import Flask, render_template_string, request, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from PIL import Image
import pillow_heif

app = Flask(__name__, static_folder="static")

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
    tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.datetime.now(tz)
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

def rdw_lookup(kenteken_raw: str):
    kenteken = kenteken_raw.replace("-", "").replace(" ", "").upper()
    if not kenteken:
        return {}
    url = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
    try:
        r = requests.get(url, params={"kenteken": kenteken}, timeout=6)
        r.raise_for_status()
        data = r.json()
        if not data:
            return {}
        row = data[0]
        merk = row.get("merk")
        type_ = row.get("handelsbenaming")
        det = row.get("datum_eerste_toelating")  # yyyymmdd
        bouwjaar = det[:4] if isinstance(det, str) and len(det) >= 4 else None
        return {"merk": merk, "type": type_, "bouwjaar": bouwjaar}
    except Exception:
        return {}

@app.route("/rdw")
def rdw_api():
    kenteken = request.args.get("kenteken", "")
    return jsonify(rdw_lookup(kenteken))

@app.route("/")
def index():
    tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.datetime.now(tz).strftime("%d-%m-%Y %H:%M")
    html = """
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Opdrachtbon • IC-North Automotive</title>
      <style>
        :root {
          --blue:#0A5FFF;
          --dark:#222;
          --muted:#f5f5f7;
          --line:#e6e6e6;
        }
        body { font-family: -apple-system, Arial, Helvetica, sans-serif; margin:0; background:var(--muted); color:#111; }
        .wrap { max-width:720px; margin:0 auto; padding:18px; }
        .card { background:#fff; border:1px solid var(--line); border-radius:16px; box-shadow:0 1px 4px rgba(0,0,0,.04); overflow:hidden; }
        .head { display:flex; align-items:center; gap:14px; padding:16px 16px 0; }
        .head img { height:40px; }
        h1 { font-size:18px; margin:0; color:var(--dark); }
        .sub { color:#666; font-size:13px; margin:0; }
        .bar { height:3px; background:linear-gradient(90deg, var(--blue), #4aa0ff); margin:12px 0; }
        form { padding:16px; }
        label { display:block; font-weight:600; font-size:13px; color:#333; margin:12px 0 6px; }
        input, textarea, select { width:100%; padding:12px 12px; border:1px solid var(--line); border-radius:12px; font-size:16px; background:#fff; }
        textarea { min-height:96px; resize:vertical; }
        .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .hint { font-size:12px; color:#666; margin-top:4px; }
        button { margin-top:16px; padding:14px 16px; background:var(--blue); color:#fff; border:none; border-radius:12px; width:100%; font-size:16px; font-weight:700; }
        .note { color:#555; font-size:12px; margin-top:6px; }
        .pill { display:inline-block; padding:6px 10px; font-size:12px; border-radius:999px; background:#eef3ff; color:#234; border:1px solid #d9e6ff; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <div class="head">
            <img src="/static/logo.png" alt="IC-North logo" />
            <div>
              <h1>Opdrachtbon formulier</h1>
              <p class="sub">Datum & tijd: <span id="now">{{now}}</span> • <span class="pill">NL tijd</span></p>
            </div>
          </div>
          <div class="bar"></div>
          <form action="/submit" method="post" enctype="multipart/form-data" id="form">
            <label>Klantnaam</label>
            <input type="text" name="klantnaam" required>

            <label>Kenteken</label>
            <input type="text" name="kenteken" id="kenteken" placeholder="XX-999-X" required>
            <div class="row">
              <div>
                <label>Merk</label>
                <input type="text" name="merk" id="merk" readonly>
              </div>
              <div>
                <label>Type</label>
                <input type="text" name="type" id="type" readonly>
              </div>
            </div>
            <div class="row">
              <div>
                <label>Bouwjaar</label>
                <input type="text" name="bouwjaar" id="bouwjaar" readonly>
              </div>
              <div>
                <label>Chassisnummer (VIN)</label>
                <input type="text" name="vin" id="vin" maxlength="17" placeholder="17 tekens" required>
                <div class="hint">Moet exact 17 karakters zijn.</div>
              </div>
            </div>

            <label>IMEI nummer</label>
            <div class="row">
              <input type="text" name="imei" id="imei">
              <button type="button" id="scanBtn">Scan IMEI (QR/Barcode)</button>
            </div>
            <div class="hint">Gebruik de scan-knop om QR/barcode te lezen (iPhone camera).</div>

            <label>Werkzaamheden</label>
            <select name="werkzaamheden">
                <option>Inbouw</option>
                <option>Ombouw</option>
                <option>Overbouw</option>
                <option>Uitbouw</option>
                <option>Servicecall</option>
            </select>

            <label>Opmerkingen</label>
            <textarea name="opmerkingen" placeholder="Toelichting op uitgevoerde werkzaamheden"></textarea>

            <label>Foto 1</label><input type="file" name="foto1" accept="image/*" capture="environment">
            <label>Foto 2</label><input type="file" name="foto2" accept="image/*" capture="environment">
            <label>Foto 3</label><input type="file" name="foto3" accept="image/*" capture="environment">

            <label>Klant email</label>
            <input type="email" name="klantemail" placeholder="optioneel">

            <button type="submit">Verstuur opdrachtbon</button>
            <p class="note">Week/Jaar/Overall tellers worden automatisch toegevoegd in de PDF.</p>
          </form>
        </div>
      </div>

      <!-- JS: RDW lookup + VIN validatie + QR/Barcode scan (Quagga + jsQR) -->
      <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/quagga@0.12.1/dist/quagga.min.js"></script>
      <script>
        // RDW lookup
        const kenteken = document.getElementById('kenteken');
        kenteken.addEventListener('change', async () => {
          const v = kenteken.value || '';
          if (!v) return;
          try {
            const res = await fetch('/rdw?kenteken=' + encodeURIComponent(v));
            const data = await res.json();
            if (data) {
              document.getElementById('merk').value = data.merk || '';
              document.getElementById('type').value = data.type || '';
              document.getElementById('bouwjaar').value = data.bouwjaar || '';
            }
          } catch(e) {}
        });

        // VIN validation (exact 17)
        const vin = document.getElementById('vin');
        document.getElementById('form').addEventListener('submit', (e) => {
          if ((vin.value || '').length !== 17) {
            e.preventDefault();
            alert('Chassisnummer (VIN) moet exact 17 karakters zijn.');
          }
        });

        // IMEI scan: foto -> decode QR (jsQR) en fallback barcode (Quagga)
        const scanBtn = document.getElementById('scanBtn');
        scanBtn.addEventListener('click', () => {
          const input = document.createElement('input');
          input.type = 'file';
          input.accept = 'image/*';
          input.capture = 'environment';
          input.onchange = async () => {
            const file = input.files[0];
            if (!file) return;
            const img = new Image();
            img.onload = () => {
              const c = document.createElement('canvas');
              c.width = img.naturalWidth; c.height = img.naturalHeight;
              const ctx = c.getContext('2d');
              ctx.drawImage(img, 0, 0);
              const imgData = ctx.getImageData(0, 0, c.width, c.height);
              const qr = jsQR(imgData.data, c.width, c.height);
              if (qr && qr.data) {
                document.getElementById('imei').value = qr.data.trim();
                return;
              }
              Quagga.decodeSingle({
                src: c.toDataURL(),
                numOfWorkers: 0,
                locate: true,
                inputStream: { size: 800 },
                decoder: { readers: ['code_128_reader', 'ean_reader','ean_8_reader','code_39_reader'] }
              }, (res) => {
                if (res && res.codeResult) {
                  document.getElementById('imei').value = res.codeResult.code.trim();
                } else {
                  alert('Geen QR/barcode gevonden. Probeer nogmaals, met scherpere foto.');
                }
              });
            };
            img.src = URL.createObjectURL(file);
          };
          input.click();
        });
      </script>
    </body>
    </html>
    """
    return render_template_string(html, now=now)

def _draw_wrapped_text(c, text, x, y, max_width, line_height, font="Helvetica", size=11):
    c.setFont(font, size)
    if not text:
        return y
    words = text.split()
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            c.drawString(x, y, line)
            y -= line_height
            line = w
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y

@app.route("/submit", methods=["POST"])
def submit():
    klantnaam = request.form.get("klantnaam")
    kenteken = request.form.get("kenteken")
    merk = request.form.get("merk") or rdw_lookup(kenteken).get("merk")
    type_ = request.form.get("type") or rdw_lookup(kenteken).get("type")
    bouwjaar = request.form.get("bouwjaar") or rdw_lookup(kenteken).get("bouwjaar")
    imei = request.form.get("imei")
    vin = request.form.get("vin")
    werkzaamheden = request.form.get("werkzaamheden")
    opmerkingen = request.form.get("opmerkingen")
    klantemail = request.form.get("klantemail")

    # Server-side VIN check
    if not vin or len(vin) != 17:
        return "Fout: Chassisnummer (VIN) moet exact 17 karakters zijn.", 400

    tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.datetime.now(tz).strftime("%d-%m-%Y %H:%M")
    week_total, year_total, overall_total = update_counters()

    pdf_file = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    c = canvas.Canvas(pdf_file, pagesize=A4)
    width, height = A4

    # Watermark (lichtgrijs)
    wm_path = os.path.join(app.static_folder, "watermark.png")
    if os.path.exists(wm_path):
        try:
            c.drawImage(ImageReader(wm_path), 3*cm, 8*cm, width=12*cm, height=12*cm, mask='auto')
        except Exception:
            pass

    # Logo + header
    c.setFont("Helvetica-Bold", 14)
    logo_path = os.path.join(app.static_folder, "logo.png")
    x = 2*cm
    top = height - 2*cm
    if os.path.exists(logo_path):
        try:
            c.drawImage(ImageReader(logo_path), x, top-1.2*cm, width=3.2*cm, height=1.2*cm, mask='auto')
        except Exception:
            pass
    c.setFillColor(colors.HexColor("#222222"))
    c.drawString(x+3.6*cm, top-0.2*cm, "IC-North Automotive — Opdrachtbon")
    c.setFont("Helvetica", 11)
    c.drawString(x+3.6*cm, top-0.9*cm, f"Datum & tijd: {now}")

    # Divider
    c.setStrokeColor(colors.HexColor("#0A5FFF"))
    c.setLineWidth(2)
    c.line(2*cm, height-2.4*cm, width-2*cm, height-2.4*cm)

    # Gegevens blok
    y = height - 3.4*cm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Voertuig & Klant")
    y -= 0.5*cm
    c.setFont("Helvetica", 11)
    c.drawString(x, y, f"Klantnaam: {klantnaam}"); y -= 0.6*cm
    c.drawString(x, y, f"Kenteken: {kenteken}"); y -= 0.6*cm
    c.drawString(x, y, f"Merk/Type/Bouwjaar: {merk or '-'} / {type_ or '-'} / {bouwjaar or '-'}"); y -= 0.6*cm
    c.drawString(x, y, f"IMEI: {imei or '-'}"); y -= 0.6*cm
    c.drawString(x, y, f"VIN (chassisnummer): {vin}"); y -= 0.9*cm

    # Werkzaamheden
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Werkzaamheden")
    y -= 0.6*cm
    c.setFont("Helvetica", 11)
    c.drawString(x, y, f"{werkzaamheden}"); y -= 0.9*cm

    # Opmerkingen (wrapped)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Opmerkingen")
    y -= 0.6*cm
    c.setFont("Helvetica", 11)
    y = _draw_wrapped_text(c, opmerkingen or "-", x, y, max_width=width-4*cm, line_height=14)

    # Foto’s
    y -= 0.3*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, "Foto's")
    y -= 0.6*cm
    photo_y = y
    for i in range(1, 4):
        foto = request.files.get(f"foto{i}")
        if foto and foto.filename != "":
            path = f"foto_{i}.png"
            try:
                if foto.filename.lower().endswith(".heic"):
                    heif = pillow_heif.read_heif(foto.read())
                    img = Image.frombytes(heif.mode, heif.size, heif.data)
                else:
                    img = Image.open(foto.stream)
                img.thumbnail((800,800))
                img.save(path, "PNG")
                c.drawImage(ImageReader(path), x, photo_y-5.2*cm, width=6*cm, height=5*cm, preserveAspectRatio=True, mask='auto')
                x += 6.5*cm
                if x > (2*cm + 6.5*cm):
                    x = 2*cm
                    photo_y -= 5.6*cm
            except Exception:
                pass
    y = photo_y - 6.4*cm

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
        recipients = [RECEIVER_EMAIL] if RECEIVER_EMAIL else []
        if klantemail:
            recipients.append(klantemail)
        msg["To"] = ", ".join(recipients) if recipients else SENDER_EMAIL
        msg["Subject"] = f"Opdrachtbon - {klantnaam} ({kenteken})"

        body = MIMEText("Zie bijlage voor de opdrachtbon.", "plain")
        msg.attach(body)

        with open(pdf_file, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
            attach.add_header("Content-Disposition", "attachment", filename=pdf_file)
            msg.attach(attach)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients or [SENDER_EMAIL], msg.as_string())

        return "Opdrachtbon verstuurd!"
    except Exception as e:
        return f"Fout bij verzenden e-mail: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
