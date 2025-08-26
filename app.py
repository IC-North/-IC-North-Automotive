
import os
import io
import datetime
import requests
import smtplib
from flask import Flask, render_template_string, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "")  # bcc/administratie
PASSWORD = os.environ.get("PASSWORD", "")
TIMEZONE_OFFSET_MIN = int(os.environ.get("TZ_OFFSET_MIN", "120"))  # default CET/CEST +120

def local_now_string():
    # Render dyno runs in UTC; apply offset minutes to show local EU time
    now_utc = datetime.datetime.utcnow()
    local = now_utc + datetime.timedelta(minutes=TIMEZONE_OFFSET_MIN)
    return local.strftime("%d-%m-%Y %H:%M")

@app.route("/")
def index():
    now = local_now_string()
    html = """
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>IC‑North Automotive – Opdrachtbon</title>
      <style>
        :root{ --brand:#0b3a6a; --muted:#e9edf3; }
        body{ font-family: -apple-system, Arial, sans-serif; margin:0; background:#f6f8fb; }
        .wrap{ max-width: 720px; margin: 0 auto; padding: 16px; }
        h1{ font-size:20px; text-align:center; color:var(--brand); margin:12px 0 4px; }
        .card{ background:#fff; border-radius:12px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,.05); }
        label{ font-weight:600; display:block; margin-top:12px; }
        input, textarea, select, button{ width:100%; padding:12px; border-radius:10px; border:1px solid #ccd5e3; font-size:16px; }
        input[readonly]{ background:#f3f6fa; color:#222; }
        button.primary{ background:var(--brand); color:#fff; border:none; }
        .row{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .small{ font-size:12px; color:#6b7280; }
        #scanner{ width:100%; height:260px; background:#000; border-radius:10px; margin-top:8px; overflow:hidden; position:relative; }
        #video{ width:100%; height:100%; object-fit:cover; }
        .btnrow{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <h1>Opdrachtbon</h1>
        <div class="card">
          <div class="small"><b>Datum & tijd:</b> {{now}}</div>

          <form action="/submit" method="post" enctype="multipart/form-data">
            <label>Kenteken</label>
            <div class="row">
              <input id="kenteken" name="kenteken" placeholder="AB-12-CD" autocapitalize="characters" required>
              <button type="button" class="primary" onclick="haalGegevens()">Haal gegevens op</button>
            </div>

            <div class="row">
              <div>
                <label>Merk</label>
                <input id="merk" name="merk" readonly>
              </div>
              <div>
                <label>Type</label>
                <input id="type" name="type" readonly>
              </div>
            </div>
            <div class="row">
              <div>
                <label>Bouwjaar</label>
                <input id="bouwjaar" name="bouwjaar" readonly>
              </div>
              <div>
                <label>Klantnaam</label>
                <input name="klantnaam" placeholder="Naam klant" required>
              </div>
            </div>

            <label>IMEI nummer</label>
            <input id="imei" name="imei" inputmode="numeric" placeholder="scan of voer in">

            <div class="btnrow">
              <button type="button" onclick="startScan()" class="primary">Scan IMEI (barcode/QR)</button>
              <button type="button" onclick="stopScan()">Stop scanner</button>
            </div>
            <div id="scanner" style="display:none;">
              <video id="video" playsinline></video>
              <canvas id="canvas" style="display:none;"></canvas>
            </div>

            <label>Chassisnummer (VIN – 17 tekens)</label>
            <input id="chassis" name="chassis" maxlength="17" pattern="[A-HJ-NPR-Z0-9]{17}" placeholder="WV1ZZZ2HZ6H000001" title="17 tekens, geen I O Q">

            <label>Opmerkingen / werkomschrijving</label>
            <textarea name="opmerkingen" rows="4" placeholder="Toelichting op uitgevoerde werkzaamheden"></textarea>

            <div class="row">
              <div>
                <label>Foto 1</label>
                <input type="file" name="foto1" accept="image/*">
              </div>
              <div>
                <label>Foto 2</label>
                <input type="file" name="foto2" accept="image/*">
              </div>
            </div>
            <label>Foto 3</label>
            <input type="file" name="foto3" accept="image/*">

            <label>Klant e‑mail (ontvangt PDF)</label>
            <input type="email" name="klantemail" placeholder="klant@example.com">

            <button class="primary" type="submit">Maak PDF & verstuur</button>
          </form>

          <p class="small">PDF wordt per e‑mail verstuurd (indien e‑mail is ingesteld) en is geoptimaliseerd voor 1 A4 (staand).</p>
        </div>
      </div>

      <!-- QuaggaJS voor barcodes -->
      <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
      <!-- jsQR voor QR-codes -->
      <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>

      <script>
        async function haalGegevens(){
          const kenteken = document.getElementById('kenteken').value.replace(/-/g,'').toUpperCase();
          if(!kenteken){ alert('Vul eerst een kenteken in'); return; }
          const r = await fetch(`/rdw/${kenteken}`);
          const data = await r.json();
          if(data.error){ alert(data.error); return; }
          document.getElementById('merk').value = data.merk || '';
          document.getElementById('type').value = data.type || '';
          document.getElementById('bouwjaar').value = data.bouwjaar || '';
        }

        let quaggaRunning = false, stream=null, rafId=null;

        function startScan(){
          // Toon video container
          document.getElementById('scanner').style.display = 'block';

          // Start Quagga (barcodes)
          if(window.Quagga && !quaggaRunning){
            Quagga.init({
              inputStream: {
                name: "Live",
                type: "LiveStream",
                target: document.querySelector('#scanner'),
                constraints: { facingMode: "environment" }
              },
              decoder: { readers: ["code_128_reader","ean_reader","ean_8_reader","code_39_reader"] }
            }, function(err){
              if(err){ console.log(err); alert("Scanner fout: " + err); return; }
              Quagga.start();
              quaggaRunning = true;
            });

            Quagga.onDetected(function(result){
              if(result && result.codeResult && result.codeResult.code){
                document.getElementById('imei').value = result.codeResult.code;
                stopScan();
                alert("IMEI gescand (barcode): " + result.codeResult.code);
              }
            });
          }

          // Start QR via getUserMedia + jsQR
          const video = document.getElementById('video');
          const canvas = document.getElementById('canvas');
          const ctx = canvas.getContext('2d');

          navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then(s => {
              stream = s;
              video.srcObject = s;
              video.play();
              const tick = () => {
                if(video.readyState === video.HAVE_ENOUGH_DATA){
                  canvas.width = video.videoWidth;
                  canvas.height = video.videoHeight;
                  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                  const code = jsQR(imageData.data, canvas.width, canvas.height);
                  if(code && code.data){
                    document.getElementById('imei').value = code.data;
                    stopScan();
                    alert("IMEI gescand (QR): " + code.data);
                    return;
                  }
                }
                rafId = requestAnimationFrame(tick);
              };
              tick();
            })
            .catch(e => console.log("Camera fout:", e));
        }

        function stopScan(){
          try{
            if(window.Quagga && quaggaRunning){ Quagga.stop(); quaggaRunning=false; }
          }catch(e){}
          try{
            if(stream){ stream.getTracks().forEach(t => t.stop()); stream=null; }
          }catch(e){}
          try{
            if(rafId){ cancelAnimationFrame(rafId); rafId=null; }
          }catch(e){}
          document.getElementById('scanner').style.display = 'none';
        }
      </script>
    </body>
    </html>
    """
    return render_template_string(html, now=now)

@app.route("/rdw/<kenteken>")
def rdw(kenteken):
    try:
        k = kenteken.replace("-","").upper()
        url = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={k}"
        r = requests.get(url, timeout=6)
        data = r.json()
        if not data:
            return jsonify({"error":"Geen gegevens gevonden"})
        rec = data[0]
        merk = rec.get("merk","")
        handels = rec.get("handelsbenaming","")
        bouwjaar = (rec.get("datum_eerste_toelating","") or "")[:4]
        return jsonify({"merk": merk, "type": handels, "bouwjaar": bouwjaar})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/submit", methods=["POST"])
def submit():
    # Lees velden
    klantnaam = request.form.get("klantnaam","")
    kenteken = request.form.get("kenteken","").upper()
    merk = request.form.get("merk","")
    type_auto = request.form.get("type","")
    bouwjaar = request.form.get("bouwjaar","")
    imei = request.form.get("imei","")
    chassis = request.form.get("chassis","")
    opmerkingen = request.form.get("opmerkingen","")
    klantemail = request.form.get("klantemail","")

    # PDF bouwen in-memory
    now = local_now_string()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w,h = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, h-2*cm, "IC-North Automotive — Opdrachtbon")
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, h-2.6*cm, f"Datum & tijd: {now}")

    y = h-3.6*cm
    line = 14
    def row(lbl, val):
        nonlocal y
        c.setFont("Helvetica-Bold", 11); c.drawString(2*cm, y, f"{lbl}")
        c.setFont("Helvetica", 11); c.drawString(6.2*cm, y, f":  {val}"); y -= line

    row("Klantnaam", klantnaam)
    row("Kenteken", kenteken)
    row("Merk", merk)
    row("Type", type_auto)
    row("Bouwjaar", bouwjaar)
    row("IMEI", imei)
    row("Chassis (VIN)", chassis)

    # Opmerkingen blok
    c.setFont("Helvetica-Bold", 11); c.drawString(2*cm, y, "Opmerkingen / werkomschrijving:"); y -= line
    c.setFont("Helvetica", 11)
    for ln in opmerkingen.splitlines() or ["—"]:
        c.drawString(2*cm, y, ln[:110]); y -= line

    c.showPage()
    c.save()
    buf.seek(0)

    # E-mail (optioneel)
    sent = False
    error = None
    if SENDER_EMAIL and PASSWORD and (RECEIVER_EMAIL or klantemail):
        try:
            msg = MIMEMultipart()
            msg["From"] = SENDER_EMAIL
            # Verstuur naar administratie en (optioneel) klant
            tos = [x for x in [RECEIVER_EMAIL, klantemail] if x]
            msg["To"] = ", ".join(tos)
            msg["Subject"] = f"Opdrachtbon – {klantnaam} – {kenteken}"

            body = MIMEText("In de bijlage vind je de opdrachtbon (PDF).", "plain")
            msg.attach(body)

            part = MIMEApplication(buf.getvalue(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=f"opdrachtbon_{kenteken}.pdf")
            msg.attach(part)

            with smtplib.SMTP("smtp.gmail.com", 587) as s:
                s.starttls()
                s.login(SENDER_EMAIL, PASSWORD)
                s.sendmail(SENDER_EMAIL, tos, msg.as_string())
            sent = True
        except Exception as e:
            error = str(e)

    if sent:
        return "PDF gemaakt en verstuurd via e‑mail."
    if error:
        return f"PDF gemaakt, maar e‑mail verzenden mislukte: {error}"
    # Geen email ingesteld: bied download
    return send_file(buf, as_attachment=True, download_name=f"opdrachtbon_{kenteken}.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
