
from mailer import build_message, send_email, MailConfigError
import os, re, datetime, requests, traceback
from io import BytesIO

def safe_save_jpeg(im, out, quality):
    try:
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True, subsampling="4:2:0")
    except Exception:
        try:
            im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        except Exception:
            im.save(out, format="JPEG", quality=quality)
from flask import Flask, render_template_string, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH_MB', '25')) * 1024 * 1024  # max upload size

def format_kenteken(raw: str) -> str:
    if not raw: return ""
    s = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    parts = re.findall(r"[A-Z]+|\d+", s)
    return "-".join(parts)

def split_emails(raw: str):
    if not raw: return []
    return [e.strip() for e in re.split(r"[;,]", raw) if e.strip()]

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = """
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IC‑North Automotive · Opdrachtbon</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/html5-qrcode@2.3.9/html5-qrcode.min.js"></script>
<style>
:root{ --primary:#0F67B1; --ink:#1b1f23; --muted:#6b7280; --bg:#f7f8fa; }
*{ box-sizing:border-box }
body{ margin:0; font-family:Inter,system-ui,Arial,sans-serif; background:var(--bg); color:var(--ink); }
.wrap{ max-width:860px; margin:24px auto; padding:16px; }
.card{ background:#fff; border-radius:16px; box-shadow:0 8px 24px rgba(16,24,40,.06); padding:20px; }
h1{ font-size:22px; margin:0 0 8px }
.sub{ color:var(--muted); font-size:13px; margin-bottom:18px }
label{ font-weight:600; font-size:13px; color:#111827 }
input, select, textarea{ width:100%; padding:12px 14px; margin:8px 0 16px; border:1px solid #e5e7eb; border-radius:10px; font-size:15px; background:#fff }
input[readonly]{ background:#f3f4f6 }
textarea{ min-height:90px; resize:vertical }
.row{ display:grid; grid-template-columns:1fr; gap:14px }
@media (min-width:680px){ .row-2{ grid-template-columns:1fr 1fr } .row-3{ grid-template-columns:1fr 1fr 1fr } }
.btn{ appearance:none; border:0; border-radius:12px; padding:14px 16px; background:var(--primary); color:#fff; font-weight:600; cursor:pointer; width:100% }
.btn.secondary{ background:#eef2ff; color:#1e3a8a }
.btn.icon{ display:flex; align-items:center; justify-content:center; gap:8px }
.actions{ display:grid; grid-template-columns:1fr; gap:12px; margin-top:6px }
@media (min-width:520px){ .actions{ grid-template-columns:1fr 1fr } }
.hint{ font-size:12px; color:#6b7280; margin-top:-10px; margin-bottom:10px }
.scanner{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.7); z-index:9999; align-items:center; justify-content:center; }
.scanner .box{ background:#0b1220; border-radius:16px; width:min(96vw,720px); padding:12px; }
.scanner header{ color:#cbd5e1; padding:6px 8px 10px; display:flex; justify-content:space-between; align-items:center }
.scanner header small{ color:#94a3b8 }
.scanner button{ background:#111827; color:#fff; border:0; border-radius:10px; padding:8px 12px; cursor:pointer }
#reader{ width:100%; height:60vh; background:#0b1220; }
#scanError{ color:#fecaca; font-size:12px; margin-top:6px; }
.footer-info{ color:#9ca3af; font-size:12px; text-align:center; margin-top:8px }
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>Opdrachtbon</h1>
    <div class="sub">Datum &amp; tijd: <strong>{{now}}</strong></div>

    <form action="/submit" method="post" id="bonform" enctype="multipart/form-data">
      <div class="row row-2">
        <div><label>Klantnaam</label><input name="klantnaam" required placeholder="Bedrijf of persoon"></div>
        <div class="rdw">
          <div style="flex:1">
            <label>Kenteken</label>
            <input id="kenteken" style="width:200px;" oninput="formatKenteken()" name="kenteken" required placeholder="Bijv. VGK-91-X" autocomplete="off">
            <div class="hint">Wordt automatisch geformatteerd en opgehaald.</div>
          </div>
          <button type="button" class="btn secondary" onclick="haalRdw()">Haal RDW</button>
        </div>
      </div>

      <div class="row row-3">
        <div><label>Merk</label><input id="merk" name="merk" readonly></div>
        <div><label>Type</label><input id="type" name="type" readonly></div>
        <div><label>Bouwjaar</label><input id="bouwjaar" name="bouwjaar" readonly></div>
      </div>

      <div class="row row-2">
        <div>
          <label>IMEI nummer</label>
          <input id="imei" name="imei" placeholder="Scan of typ het nummer">
          <div class="actions"><button type="button" class="btn icon" onclick="openScanner('imei')">Scan IMEI</button></div>
          <div class="hint">Ondersteunt QR, Code128, Code39, EAN-13/8. Voegt checkdigit toe bij 14 cijfers.</div>
        </div>
        <div>
          <label>VIN (chassisnummer – 17 tekens)</label>
          <input id="vin" name="vin" maxlength="17" minlength="17" placeholder="Scan of typ VIN (17)">
          <div class="actions"><button type="button" class="btn icon" onclick="openScanner('vin')">Scan VIN</button></div>
          <div class="hint">Verwijdert automatisch I/O/Q en accepteert exact 17 tekens.</div>
        </div>
      </div>

      <div><label>Werkzaamheden</label>
        <select name="werkzaamheden"><option>Inbouw</option><option>Ombouw</option><option>Overbouw</option><option>Uitbouw</option><option>Servicecall</option></select>
      </div>

      <div><label>Opmerkingen</label><textarea name="opmerkingen" placeholder="Toelichting op uitgevoerde werkzaamheden"></textarea></div>

      <div class="row row-2">
        <div><label>Klant e‑mail</label><input type="email" name="klantemail" placeholder="klant@domein.nl"></div>
        <div><label>Eigen e‑mail (afzender)</label><input type="email" name="senderemail" value="icnorthautomotive@gmail.com" readonly></div>
      </div>

      
      <div class="row row-2" style="margin-top:16px">
        <div>
          <label>Kenteken foto</label>
          <input type="file" name="foto_kenteken" accept="image/*" capture="environment">
          <div class="hint">Maak of kies een duidelijke foto van het kenteken.</div>
        </div>
        <div>
          <label>IMEI foto</label>
          <input type="file" name="foto_imei" accept="image/*" capture="environment">
          <div class="hint">Foto van het IMEI‑nummer (bijv. sticker/label).</div>
        </div>
      </div>

      <div class="row row-2">
        <div>
          <label>Chassisnummer foto</label>
          <input type="file" name="foto_chassis" accept="image/*" capture="environment">
          <div class="hint">Foto van het VIN/chassisnummer.</div>
        </div>
        <div>
          <label>Extra foto 1 (optioneel)</label>
          <input type="file" name="foto_extra1" accept="image/*" capture="environment">
          <div class="hint">Optioneel extra beeld (detail of context).</div>
        </div>
      </div>

      <div class="row row-2">
        <div>
          <label>Extra foto 2 (optioneel)</label>
          <input type="file" name="foto_extra2" accept="image/*" capture="environment">
          <div class="hint">Optioneel extra beeld.</div>
        </div>
      </div>
    <button class="btn" type="submit">PDF maken &amp; mailen</button>
    </form>

    <div class="footer-info">Scan werkt op iPhone (Safari) via camera • RDW via open data</div>
  </div>
</div>

<div class="scanner" id="scanner">
  <div class="box">
    <header>
      <div>Camera scanner</div>
      <div><small id="scanTip">Richt op code</small> <button onclick="closeScanner()">Sluiten</button></div>
    </header>
    <div id="reader"></div>
    <div id="scanError"></div>
  </div>
</div>

<script>
let currentTarget = null, html5Scanner = null, stopTimer = null;
function showErr(msg){ document.getElementById('scanError').textContent = msg || ''; }
function blurInputs(){ try { document.activeElement && document.activeElement.blur(); } catch(e){} window.scrollTo({ top: 0, behavior: 'smooth' }); }

async function openScanner(target){
  currentTarget = target; blurInputs(); document.getElementById('scanner').style.display='flex'; showErr('');
  document.getElementById('scanTip').textContent = target==='vin' ? 'Richt op VIN (Code39)' : 'Richt op QR/streepjescode voor IMEI';
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
    let devices=[]; try{ devices = await Html5Qrcode.getCameras(); }catch(e){}
    let back=null; if(devices && devices.length){ back = (devices.find(d=>/back|rear|environment|achter/i.test(d.label)) || devices[devices.length-1]).id; }
    stream.getTracks().forEach(t=>t.stop());

    const config = { fps: 12, qrbox: 320, aspectRatio: 1.777, rememberLastUsedCamera: true, showTorchButtonIfSupported: true };
    // Fallback: alleen setten als enum bestaat (Safari-fix)
    const F = window.Html5QrcodeSupportedFormats;
    if (F) { config.formatsToSupport = [F.QR_CODE, F.CODE_39, F.CODE_128, F.EAN_13, F.EAN_8]; }

    html5Scanner = new Html5Qrcode("reader");
    await new Promise(res=>setTimeout(res,80));
    await html5Scanner.start(back ? { deviceId:{ exact: back } } : { facingMode:"environment" }, config, onScanSuccess, onScanError);
  } catch(e){ showErr("Kon camera niet starten: " + (e && e.message ? e.message : e)); }

  clearTimeout(stopTimer);
  stopTimer = setTimeout(()=>{ alert("Geen code gevonden. Probeer meer licht of dichterbij."); closeScanner(); }, 30000);
}

function onScanSuccess(decodedText){
  if(currentTarget==='vin'){
    const cleaned = decodedText.replace(/[^A-Za-z0-9]/g,'').toUpperCase().replace(/[IOQ]/g,'');
    if(cleaned.length===17){ document.getElementById('vin').value = cleaned; beep(); closeScanner(); }
  } else {
    const digits = decodedText.replace(/\D/g,'');
    const m15 = digits.match(/\d{15}/), m14 = digits.match(/\d{14}/);
    let out=null; if(m15){ out=m15[0]; } else if(m14){ out=m14[0] + String(luhnCheckDigit14(m14[0])); }
    if(out){ document.getElementById('imei').value = out; beep(); closeScanner(); }
  }
}
function onScanError(_e){}

function closeScanner(){ clearTimeout(stopTimer); document.getElementById('scanner').style.display='none'; if(html5Scanner){ html5Scanner.stop().then(()=>{ html5Scanner.clear(); html5Scanner=null; }).catch(()=>{});} }
function luhnCheckDigit14(s){ let sum=0; for(let i=0;i<14;i++){ let d=parseInt(s[i],10); if(i%2===1){ d*=2; if(d>9) d-=9; } sum+=d; } return (10-(sum%10))%10; }
function beep(){ try{ const ctx=new (window.AudioContext||window.webkitAudioContext)(); const o=ctx.createOscillator(), g=ctx.createGain(); o.type='sine'; o.frequency.value=880; o.connect(g); g.connect(ctx.destination); g.gain.setValueAtTime(0.001,ctx.currentTime); g.gain.exponentialRampToValueAtTime(0.2,ctx.currentTime+0.01); o.start(); setTimeout(()=>{ g.gain.exponentialRampToValueAtTime(0.0001,ctx.currentTime+0.05); o.stop(ctx.currentTime+0.06); },60);}catch(e){} }

// rest utilities
const kentekenEl = document.getElementById('kenteken');
kentekenEl.addEventListener('change', () => {
  const raw = kentekenEl.value;
  fetch('/format_kenteken', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({raw})})
    .then(r=>r.json()).then(d=>{ kentekenEl.value = d.formatted; });
});
function haalRdw(){ const k=kentekenEl.value.trim(); if(!k){ alert('Vul eerst een kenteken in.'); return; } fetch('/rdw?kenteken='+encodeURIComponent(k)).then(r=>r.json()).then(d=>{ if(d&&d.success){ document.getElementById('merk').value=d.merk||''; document.getElementById('type').value=d.type||''; document.getElementById('bouwjaar').value=d.bouwjaar||''; } else { alert(d.message || 'Geen gegevens gevonden.'); } }).catch(()=>alert('Fout bij RDW ophalen.')); }
function formatKenteken(){ let input=document.getElementById("kenteken"); let val=input.value.toUpperCase().replace(/[^A-Z0-9]/g,""); if(val.length===6){ val=val.replace(/(.{2})(.{2})(.{2})/,"$1-$2-$3"); } else if(val.length===7){ val=val.replace(/(.{2})(.{3})(.{2})/,"$1-$2-$3"); } else if(val.length===8){ val=val.replace(/(.{2})(.{2})(.{3})(.{1})/,"$1-$2-$3-$4"); } input.value=val; }
</script>
</body>
</html>
    """
    return render_template_string(html, now=now)

@app.post("/format_kenteken")
def api_format_kenteken():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify({"formatted": format_kenteken(data.get("raw",""))})

@app.get("/rdw")
def rdw():
    raw = request.args.get("kenteken","")
    k = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if not k:
        return jsonify({"success": False, "message": "Geen kenteken opgegeven."})
    try:
        url = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
        resp = requests.get(url, params={"kenteken": k}, timeout=8)
        data = resp.json() if resp.ok else []
        if not data:
            return jsonify({"success": False, "message": "Kenteken niet gevonden bij RDW."})
        row = data[0]
        merk = row.get("merk",""); handels = row.get("handelsbenaming",""); det = row.get("datum_eerste_toelating","")
        bouwjaar = det[:4] if det and len(det)>=4 else ""
        return jsonify({"success": True, "merk": merk, "type": handels, "bouwjaar": bouwjaar})
    except Exception as e:
        return jsonify({"success": False, "message": f"RDW fout: {e}"})

@app.post("/submit")
def submit():
    klantnaam = request.form.get("klantnaam","")
    kenteken = format_kenteken(request.form.get("kenteken",""))
    merk = request.form.get("merk",""); type_ = request.form.get("type",""); bouwjaar = request.form.get("bouwjaar","")
    imei = request.form.get("imei",""); vin = request.form.get("vin","")
    werkzaamheden = request.form.get("werkzaamheden",""); opmerkingen = request.form.get("opmerkingen","")
    klantemail = (request.form.get("klantemail","") or "").strip()


    # Foto uploads (optioneel)
    foto_fields = ["foto_kenteken", "foto_imei", "foto_chassis", "foto_extra1", "foto_extra2"]
    fotos = []
    for fname in foto_fields:
        f = request.files.get(fname)
        if f and getattr(f, "filename", ""):
            data = f.read()
            if data:
                fotos.append((fname, data, f.filename))


    # Beperk bestandsgrootte: downscale & compress (JPEG) — agressiever
    processed = []
    try:
        from PIL import Image, ImageOps
        target_side = int(os.getenv("IMG_MAX_SIDE", "900"))  # strakker: 1024px
        base_quality = int(os.getenv("IMG_JPEG_QUALITY", "65"))
        min_quality = int(os.getenv("IMG_JPEG_QUALITY_MIN", "45"))
        target_kb = int(os.getenv("IMG_TARGET_PER_IMAGE_KB", "200"))
        for key, img_bytes, orig_name in fotos:
            try:
                im = Image.open(BytesIO(img_bytes))
                # Corrigeer oriëntatie en converteer naar RGB (strip EXIF)
                try:
                    im = ImageOps.exif_transpose(im)
                except Exception:
                    pass
                if im.mode not in ("RGB",):
                    im = im.convert("RGB")
                # Downscale met thumbnail (behoud aspect)
                im.thumbnail((target_side, target_side))
                # Kwaliteit stap-gewijs omlaag tot doelgrootte
                q = base_quality
                out = BytesIO()
                safe_save_jpeg(im, out, q)
                while out.tell() > (target_kb * 1024) and q > min_quality:
                    q = max(min_quality, q - 5)
                    out.seek(0); out.truncate(0)
                    safe_save_jpeg(im, out, q)
                processed.append((key, out.getvalue(), orig_name))
            except Exception:
                processed.append((key, img_bytes, orig_name))
        fotos = processed

    except Exception:
        pass

    # Upload guards
    safe_fotos = []
    for key, data, name in fotos:
        if not data or len(data) == 0: 
            continue
        safe_fotos.append((key, data, name))
    fotos = safe_fotos[:5]  # max 5

        # Totale payload limiter (bijv. 12 MB voor alle foto's samen)
    try:
        total_bytes = sum(len(b) for _, b, _ in fotos)
        max_total = int(os.getenv("IMG_TOTAL_LIMIT_MB", "4")) * 1024 * 1024
        if total_bytes > max_total:
            # Trim of weiger extra foto's boven limiet
            acc = 0
            limited = []
            for tup in fotos:
                acc += len(tup[1])
                if acc <= max_total:
                    limited.append(tup)
                else:
                    break
            fotos = limited
    except Exception:
        pass
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        pdf_buf = BytesIO()
        c = canvas.Canvas(pdf_buf, pagesize=A4)
        w, h = A4
        c.setFont("Helvetica-Bold", 13); c.drawString(2*cm, h-2*cm, f"Opdrachtbon · {now}")
        c.setFont("Helvetica", 11); y = h-3.2*cm
        for ln in [f"Klantnaam: {klantnaam}", f"Kenteken: {kenteken}  |  Merk: {merk}  |  Type: {type_}  |  Bouwjaar: {bouwjaar}", f"IMEI: {imei}", f"VIN: {vin}", f"Werkzaamheden: {werkzaamheden}"]:
            c.drawString(2*cm, y, ln); y -= 1.0*cm
        c.setFont("Helvetica-Bold", 11); c.drawString(2*cm, y, "Opmerkingen:"); y -= 0.6*cm
        c.setFont("Helvetica", 10); t = c.beginText(2*cm, y)
        for line in (opmerkingen or "-").splitlines(): t.textLine(line)
        c.drawText(t)
    
    # Foto's toevoegen aan PDF
    try:
        if fotos:
            # filter te grote restbestanden (>1.5MB) voor PDF-tekening
            fotos = [t for t in fotos if len(t[1]) <= int(os.getenv("IMG_MAX_SINGLE_FOR_PDF_BYTES", str(1_500_000))) ]
            y -= 0.8*cm
            c.setFont("Helvetica-Bold", 11); c.drawString(2*cm, y, "Foto's:"); y -= 0.6*cm
            max_w = w - 4*cm
            for key, img_bytes, orig_name in fotos:
                try:
                    ir = ImageReader(BytesIO(img_bytes))
                    iw, ih = ir.getSize()
                    scale = min(max_w/iw, 10*cm/ih) if iw and ih else 1.0
                    tw, th = iw*scale, ih*scale
                    # Pagina-breek indien nodig
                    if y - th < 2*cm:
                        c.showPage(); c.setFont("Helvetica", 10); y = h - 2.5*cm
                    c.setFont("Helvetica", 9); c.setFillColor(colors.grey)
                    label = {"foto_kenteken":"Kenteken", "foto_imei":"IMEI", "foto_chassis":"Chassis", "foto_extra1":"Extra 1", "foto_extra2":"Extra 2"}.get(key, key)
                    c.drawString(2*cm, y, f"{label}: {orig_name or ''}"); y -= 0.3*cm
                    c.setFillColor(colors.black)
                    c.drawImage(ir, 2*cm, y - th, width=tw, height=th, preserveAspectRatio=True, mask='auto')
                    y -= th + 0.6*cm
                except Exception as _e:
                    # bij mislukken van 1 foto, ga door met de rest
                    pass
    except Exception:
        pass
    c.setFillColor(colors.grey); c.setFont("Helvetica-Oblique", 9)
    c.drawString(2*cm, 1.5*cm, "IC‑North Automotive · gegenereerd via webformulier"); c.save()

    pdf_bytes = pdf_buf.getvalue(); filename = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
    admin_list = split_emails(os.getenv("RECEIVER_EMAIL"))
    recipients = [*admin_list, *( [klantemail] if klantemail else [] )]
    seen=set(); recipients=[x for x in recipients if not (x in seen or seen.add(x))]

    
    # Beslis over mail-attachments t.o.v. limiet
    email_max = int(os.getenv("EMAIL_MAX_MB", "5")) * 1024 * 1024
    originals = [ (img_bytes, (orig_name or f"{key}.jpg"), "image/jpeg") for key, img_bytes, orig_name in fotos ]
    attachments_to_send = [(pdf_bytes, filename, "application/pdf")]
    total_with_originals = len(pdf_bytes) + sum(len(b) for b, _, _ in originals)
    if total_with_originals <= email_max:
        attachments_to_send += originals
    else:
        # te groot: alleen PDF meesturen
        pass

    subject = os.getenv("MAIL_SUBJECT", "Opdrachtbon – {klantnaam} – {kenteken}").format(klantnaam=klantnaam or "", kenteken=kenteken or "")
    body = os.getenv("MAIL_BODY", "In de bijlage vind je de opdrachtbon (PDF).")
    if sender and recipients:
        try:
            msg = build_message(subject, body, sender, ", ".join(recipients), attachments=attachments_to_send)
            if klantemail: msg['Reply-To'] = klantemail
            send_email(msg)
        except Exception as e:
            print("[mail] error:", e)

    pdf_buf.seek(0)
    return send_file(pdf_buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

@app.get("/healthz")
def healthz(): return "ok", 200
@app.get("/robots.txt")
def robots(): return "User-agent: *\nDisallow:", 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.errorhandler(500)
def internal_error(e):
    tb = traceback.format_exc()
    print('[500]', e, tb)
    if os.getenv('DIAG','0')=='1':
        return (f"<h1>Interne serverfout</h1><pre>{tb}</pre>"), 500
    return ("<h1>Interne serverfout</h1><p>Er ging iets mis bij het verwerken. "
            "Ga <a href='/'>&larr; terug</a> en probeer opnieuw. "
            "Als dit blijft gebeuren, probeer minder/lager-resolutie foto's of neem contact op.</p>"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
