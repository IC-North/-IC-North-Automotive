import os
import io
import datetime
import requests
from flask import Flask, render_template_string, request, send_file, jsonify, abort
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

app = Flask(__name__)

RDW_API = "https://opendata.rdw.nl/api/records/1.0/search/"

def rdw_lookup(kenteken_raw: str):
    kt = (kenteken_raw or "").replace("-", "").upper().strip()
    if not kt:
        return {"merk": "", "type": "", "bouwjaar": ""}
    try:
        params = {"dataset": "m9d7-ebf2", "q": kt}
        r = requests.get(RDW_API, params=params, timeout=6)
        r.raise_for_status()
        data = r.json()
        if data.get("records"):
            fields = data["records"][0]["fields"]
            merk = fields.get("merk", "")
            handelsbenaming = fields.get("handelsbenaming", "")
            bouwjaar_raw = fields.get("datum_eerste_toelating", "")
            bouwjaar = (bouwjaar_raw or "")[:4]
            return {"merk": merk, "type": handelsbenaming, "bouwjaar": bouwjaar}
    except Exception:
        pass
    return {"merk": "", "type": "", "bouwjaar": ""}

@app.get("/api/rdw/<kenteken>")
def api_rdw(kenteken):
    return jsonify(rdw_lookup(kenteken))

@app.get("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = r"""
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IC‑North Opdrachtbon</title>
  <style>
    :root{ --brand:#0a3d62; --accent:#1e90ff; --ink:#111; --muted:#6b7280; --bg:#f5f7fb; }
    *{ box-sizing:border-box; }
    body{ font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif; margin:0; background:var(--bg); color:var(--ink); }
    .wrap{ max-width:720px; margin:0 auto; padding:20px; }
    .card{ background:#fff; border-radius:14px; box-shadow:0 6px 20px rgba(0,0,0,.06); padding:18px; }
    h1{ font-size:20px; margin:0 0 4px; color:var(--brand); letter-spacing:.2px; }
    .lead{ color:var(--muted); font-size:13px; margin-bottom:14px; }
    label{ font-weight:600; font-size:13px; color:#334155; display:block; margin:10px 0 6px; }
    input, select, textarea{ width:100%; padding:12px 14px; border:1px solid #e5e7eb; border-radius:10px; font-size:16px; outline:none; background:#fff; }
    input:focus, select:focus, textarea:focus{ border-color:var(--accent); box-shadow:0 0 0 3px rgba(30,144,255,.12); }
    .row{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .btn{ display:inline-block; width:100%; padding:14px 16px; border:none; border-radius:12px; font-weight:700; background:var(--brand); color:#fff; font-size:16px; }
    .btn.secondary{ background:#0f6bff; }
    .btn.scan{ background:#10b981; }
    .btn:disabled{ opacity:.6; }
    .hint{ font-size:12px; color:var(--muted); margin-top:4px; }
    .inline{ display:flex; gap:8px; align-items:center; }
    .inline > *{ flex:1; }
    .scanner{ position:fixed; inset:0; background:rgba(0,0,0,.9); display:none; align-items:center; justify-content:center; z-index:30; }
    .scanbox{ width:min(92vw,520px); aspect-ratio:3/4; background:#000; position:relative; border-radius:16px; overflow:hidden; }
    .scanbox canvas, .scanbox video{ width:100%; height:100%; object-fit:cover; }
    .scanbar{ position:absolute; left:8px; right:8px; top:8px; display:flex; gap:8px; z-index:2; }
    .tiny{ font-size:12px; padding:8px 10px; border-radius:10px; }
    .pill{ background:#111; color:#fff; border:1px solid #333; }
    footer{ text-align:center; color:var(--muted); font-size:12px; margin-top:16px; }
    .readonly{ background:#f9fafb; }
  </style>
  <!-- Quagga (barcode) & jsQR (qr) -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js" integrity="sha512-q2wktg7H4zYbN6bQnY6mQ9vVnG2sG8hKQzj2d3LZzGzJXxQpQXJXoL0Z0JwQ0LzJkZim1v3lP0sS7b8q7Vt1rg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
  <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>IC‑North Opdrachtbon</h1>
      <div class="lead">Datum & tijd: <b>{{now}}</b></div>

      <form method="post" action="/submit" id="f">
        <label>Klantnaam</label>
        <input name="klantnaam" required placeholder="Naam klant">

        <label>Kenteken</label>
        <input name="kenteken" id="kenteken" required placeholder="XX-999-X" autocomplete="off" inputmode="latin-prose" style="text-transform:uppercase;">
        <div class="hint">Na invoer wordt merk / type / bouwjaar automatisch opgehaald.</div>

        <div class="row">
          <div>
            <label>Merk</label>
            <input id="merk" name="merk" class="readonly" readonly>
          </div>
          <div>
            <label>Type</label>
            <input id="type" name="type" class="readonly" readonly>
          </div>
        </div>

        <label>Bouwjaar</label>
        <input id="bouwjaar" name="bouwjaar" class="readonly" readonly>

        <label>IMEI</label>
        <div class="inline">
          <input name="imei" id="imei" placeholder="Scan of typ IMEI">
          <button type="button" class="btn scan" onclick="openScanner('imei')">Scan</button>
        </div>

        <label>Chassisnummer (VIN – 17 tekens)</label>
        <div class="inline">
          <input name="vin" id="vin" maxlength="17" minlength="17" required placeholder="VB: W0L0XCF0811234567" style="text-transform:uppercase;">
          <button type="button" class="btn scan" onclick="openScanner('vin')">Scan</button>
        </div>
        <div class="hint">We proberen barcodes (Code128/Code39). Handmatig aanvullen blijft mogelijk.</div>

        <label>Werkzaamheden</label>
        <select name="werkzaamheden">
          <option>Inbouw</option>
          <option>Ombouw</option>
          <option>Overbouw</option>
          <option>Uitbouw</option>
          <option>Servicecall</option>
        </select>

        <label>Opmerkingen</label>
        <textarea name="opmerkingen" rows="4" placeholder="Toelichting op uitgevoerde werkzaamheden"></textarea>

        <div style="margin-top:14px;">
          <button class="btn" type="submit">PDF genereren</button>
        </div>
      </form>
    </div>
    <footer>© IC‑North Automotive</footer>
  </div>

  <!-- Scanner overlay -->
  <div class="scanner" id="scanner">
    <div class="scanbox">
      <div class="scanbar">
        <button class="tiny pill" type="button" onclick="closeScanner()">Sluiten</button>
        <button class="tiny pill" type="button" onclick="toggleMode()">Wissel QR/Barcode</button>
      </div>
      <video id="video" playsinline></video>
      <canvas id="qrcanvas" style="display:none;"></canvas>
    </div>
  </div>

<script>
let currentField = null;
let isQRMode = false;
let stream = null;
let quaggaRunning = false;
const scanner = document.getElementById('scanner');
const video = document.getElementById('video');
const qrcanvas = document.getElementById('qrcanvas');
const kentekenInput = document.getElementById('kenteken');

function closeScanner(){
  scanner.style.display='none';
  stopAll();
}
function toggleMode(){
  isQRMode = !isQRMode;
  stopAll();
  startScan();
}
function openScanner(fieldId){
  currentField = document.getElementById(fieldId);
  isQRMode = (fieldId === 'imei') ? false : false; // default barcode; switch via button for QR
  scanner.style.display='flex';
  startScan();
}
function stopAll(){
  try{ if (quaggaRunning && window.Quagga){ Quagga.stop(); quaggaRunning=false; } }catch(e){}
  try{ if (stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; } }catch(e){}
}
async function startScan(){
  if (isQRMode){
    // QR scanning via getUserMedia + jsQR
    try{
      stream = await navigator.mediaDevices.getUserMedia({ video:{ facingMode:'environment' }, audio:false });
      video.srcObject = stream;
      await video.play();
      const ctx = qrcanvas.getContext('2d');
      (function tick(){
        if (!stream) return;
        qrcanvas.width = video.videoWidth;
        qrcanvas.height = video.videoHeight;
        ctx.drawImage(video,0,0,qrcanvas.width,qrcanvas.height);
        const imgData = ctx.getImageData(0,0,qrcanvas.width,qrcanvas.height);
        const code = jsQR(imgData.data, imgData.width, imgData.height);
        if (code && code.data){
          currentField.value = code.data.trim();
          closeScanner();
          return;
        }
        requestAnimationFrame(tick);
      })();
    }catch(e){
      alert('Camera-toegang nodig voor QR-scannen.');
      closeScanner();
    }
  }else{
    // Barcode scanning via Quagga
    if (!window.Quagga){ alert('Quagga niet geladen'); closeScanner(); return; }
    Quagga.init({
      inputStream: { type:'LiveStream', target: document.querySelector('.scanbox'), constraints:{ facingMode:'environment' } },
      decoder: { readers: ['code_128_reader','code_39_reader','ean_reader','ean_8_reader','upc_reader'] }
    }, function(err){
      if (err){ alert('Camera start fout: '+err); closeScanner(); return; }
      Quagga.start(); quaggaRunning=true;
    });
    Quagga.onDetected(function(res){
      if (!res || !res.codeResult) return;
      const val = (res.codeResult.code||'').trim();
      if (val){
        currentField.value = val;
        closeScanner();
      }
    });
  }
}

// RDW fetch bij kenteken wijziging (na pauze)
let ktTimer=null;
kentekenInput.addEventListener('input', ()=>{
  clearTimeout(ktTimer);
  ktTimer=setTimeout(async ()=>{
    const raw = kentekenInput.value.toUpperCase().replace(/[^A-Z0-9]/g,'');
    if (raw.length < 5) return;
    try{
      const r = await fetch('/api/rdw/'+raw);
      const j = await r.json();
      document.getElementById('merk').value = j.merk || '';
      document.getElementById('type').value = j.type || '';
      document.getElementById('bouwjaar').value = j.bouwjaar || '';
    }catch(e){}
  }, 350);
});

// VIN upper-case en filteren
const vin = document.getElementById('vin');
vin.addEventListener('input', ()=>{
  vin.value = vin.value.toUpperCase().replace(/[^A-Z0-9]/g,'');
});
</script>
</body>
</html>
    """
    return render_template_string(html, now=now)

@app.post("/submit")
def submit():
    klantnaam = (request.form.get("klantnaam") or "").strip()
    kenteken = (request.form.get("kenteken") or "").upper().strip()
    imei = (request.form.get("imei") or "").strip()
    vin = (request.form.get("vin") or "").upper().strip()
    werkzaamheden = (request.form.get("werkzaamheden") or "").strip()
    opmerkingen = (request.form.get("opmerkingen") or "").strip()

    # VIN check
    if len(vin) != 17:
        return abort(400, "VIN moet 17 tekens zijn.")

    car = rdw_lookup(kenteken)
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    # PDF genereren in memory
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Kop
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, height-2*cm, f"Opdrachtbon — {now}")

    # Lijntjes en gegevens
    c.setFont("Helvetica", 11)
    y = height-3*cm
    step = 1*cm
    c.drawString(2*cm, y, f"Klantnaam: {klantnaam}"); y-=step
    c.drawString(2*cm, y, f"Kenteken: {kenteken}"); y-=step
    c.drawString(2*cm, y, f"Merk: {car.get('merk','')}  Type: {car.get('type','')}  Bouwjaar: {car.get('bouwjaar','')}"); y-=step
    c.drawString(2*cm, y, f"IMEI: {imei}"); y-=step
    c.drawString(2*cm, y, f"VIN: {vin}"); y-=step
    c.drawString(2*cm, y, f"Werkzaamheden: {werkzaamheden}"); y-=step
    c.drawString(2*cm, y, "Opmerkingen:"); y-=0.5*cm

    # Meerdere regels opmerkingen
    textobj = c.beginText(2*cm, y)
    textobj.setFont("Helvetica", 11)
    for line in (opmerkingen or "").splitlines() or ["-"]:
        textobj.textLine(line)
    c.drawText(textobj)

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(2*cm, 1.5*cm, "IC‑North Automotive — Automatisch gegenereerde opdrachtbon")
    c.save()

    buf.seek(0)
    filename = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
