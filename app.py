
from mailer import build_message, send_email, MailConfigError
import os, re, datetime, requests
from io import BytesIO
from flask import Flask, render_template_string, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageOps


def _shrink_for_pdf(img_bytes: bytes, max_side: int = 1200, target_kb: int = 260) -> bytes:
    """
    Downscale & recompress image bytes for PDF drawing only.
    Keeps memory/canvas usage low. Returns JPEG bytes.
    """
    try:
        im = Image.open(BytesIO(img_bytes))
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        if im.mode not in ("RGB",):
            im = im.convert("RGB")
        # downscale
        im.thumbnail((max_side, max_side))
        # compress loop
        q = 70
        out = BytesIO()
        im.save(out, format="JPEG", quality=q, optimize=True, progressive=True)
        while out.tell() > target_kb*1024 and q > 50:
            q = max(50, q - 5)
            out.seek(0); out.truncate(0)
            im.save(out, format="JPEG", quality=q, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:
        return img_bytes
app = Flask(__name__)

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
<script src="/static/html5-qrcode.min.js" defer></script>
<script src="/static/tesseract.min.js" defer></script>
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
          <div class="actions"><button type="button" class="btn icon" onclick="openBarcodeScanner('imei')">Scan IMEI</button></div>
          <div class="hint">Ondersteunt QR, Code128, Code39, EAN-13/8. Voegt checkdigit toe bij 14 cijfers.</div>
        </div>
        <div>
          <label>VIN (chassisnummer – 17 tekens)</label>
          <input id="vin" name="vin" maxlength="17" minlength="17" placeholder="Scan of typ VIN (17)"><div class="actions"><button type="button" class="btn icon" onclick="openVinOcr('vin')">Scan VIN (OCR)</button></div>
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
        </div>
        <div>
          <label>IMEI foto</label>
          <input type="file" name="foto_imei" accept="image/*" capture="environment">
        </div>
      </div>
      <div class="row row-2">
        <div>
          <label>Chassisnummer foto</label>
          <input type="file" name="foto_chassis" accept="image/*" capture="environment">
        </div>
        <div>
          <label>Extra foto 1 (optioneel)</label>
          <input type="file" name="foto_extra1" accept="image/*" capture="environment">
        </div>
      </div>
      <div class="row row-2">
        <div>
          <label>Extra foto 2 (optioneel)</label>
          <input type="file" name="foto_extra2" accept="image/*" capture="environment">
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
// Ensure library is available (wait up to ~5s), helpful for iOS where CDN load kan vertragen
async function ensureHtml5QrcodeLoaded(){
  if (window.Html5Qrcode) return;
  let tries = 0;
  await new Promise((resolve, reject) => {
    const t = setInterval(() => {
      if (window.Html5Qrcode) { clearInterval(t); resolve(); }
      else if (++tries > 50) { clearInterval(t); reject(new Error("Html5Qrcode niet geladen")); }
    }, 100);
  });
}
</script>
let currentTarget = null, html5Scanner = null, stopTimer = null;
function showErr(msg){ document.getElementById('scanError').textContent = msg || ''; }
function blurInputs(){ try { document.activeElement && document.activeElement.blur(); } catch(e){} window.scrollTo({ top: 0, behavior: 'smooth' }); }

async function openScanner(target){
  currentTarget = target; blurInputs(); document.getElementById('scanner').style.display='flex'; showErr('');
  document.getElementById('scanTip').textContent = target==='vin' ? 'Richt op VIN (Code39)' : 'Richt op QR/streepjescode voor IMEI';
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } } });
    let devices=[]; try{ devices = (window.Html5Qrcode ? await Html5Qrcode.getCameras() : []); }catch(e){}
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

<script>
/* -- imei/vin validation injected -- */
function isValidIMEI(s){
  s = (s||"").replace(/\D/g,'');
  if (!/^\d{15}$/.test(s)) return false;
  let sum=0;
  for (let i=0;i<15;i++){
    let d = s.charCodeAt(i)-48;
    if (i%2===1){ d*=2; if (d>9) d-=9; }
    sum += d;
  }
  return sum % 10 === 0;
}
function luhnCheckDigit14(s){
  s = (s||"").replace(/\D/g,'');
  if (!/^\d{14}$/.test(s)) return null;
  let sum=0;
  for (let i=0;i<14;i++){
    let d = s.charCodeAt(i)-48;
    if (i%2===1){ d*=2; if (d>9) d-=9; }
    sum += d;
  }
  return (10-(sum%10))%10;
}
function isValidVIN(v){
  v = (v||"").toUpperCase();
  if (!/^[A-HJ-NPR-Z0-9]{17}$/.test(v)) return false;
  const map = {A:1,B:2,C:3,D:4,E:5,F:6,G:7,H:8,J:1,K:2,L:3,M:4,N:5,P:7,R:9,S:2,T:3,U:4,V:5,W:6,X:7,Y:8,Z:9};
  const w = [8,7,6,5,4,3,2,10,0,9,8,7,6,5,4,3,2];
  const val = ch => (ch>='0'&&ch<='9') ? (ch.charCodeAt(0)-48) : (map[ch]||0);
  let sum=0;
  for (let i=0;i<17;i++) sum += val(v[i]) * w[i];
  const check = sum % 11;
  const checkChar = check === 10 ? 'X' : String(check);
  return v[8] === checkChar;
}

(function attachValidation(){
  const imeiEl = document.getElementById('imei');
  if (imeiEl){
    const handler = () => {
      let v = imeiEl.value.replace(/\D/g,'');
      if (v.length===14){
        const d = luhnCheckDigit14(v);
        if (d!==null){ v = v + String(d); imeiEl.value = v; }
      }
      const ok = v==='' || (v.length===15 && isValidIMEI(v));
      imeiEl.setCustomValidity(ok ? '' : 'Ongeldige IMEI (15 cijfers, Luhn)');
    };
    imeiEl.addEventListener('input', handler);
    imeiEl.addEventListener('change', handler);
  }
  const vinEl = document.getElementById('vin');
  if (vinEl){
    const handlerVin = () => {
      let v = vinEl.value.toUpperCase().replace(/[^A-Z0-9]/g,'');
      // forbid I, O, Q
      v = v.replace(/[IOQ]/g,'');
      if (v.length>17) v = v.slice(0,17);
      vinEl.value = v;
      const ok = v==='' || (v.length===17 && isValidVIN(v));
      vinEl.setCustomValidity(ok ? '' : 'Ongeldige VIN (17 tekens, met checkdigit)');
    };
    vinEl.addEventListener('input', handlerVin);
    vinEl.addEventListener('change', handlerVin);
  }
})();
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
    # Uploaded foto's ophalen (optioneel)
    foto_fields = ["foto_kenteken","foto_imei","foto_chassis","foto_extra1","foto_extra2"]
    fotos = []
    for fname in foto_fields:
        f = request.files.get(fname)
        if f and getattr(f, "filename", ""):
            data = f.read()
            if data:
                fotos.append((fname, data, f.filename))

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf_buf = BytesIO(); c = canvas.Canvas(pdf_buf, pagesize=A4); w,h = A4
    # ===== V9 LAYOUT (volledige stijl: header, cards, fotogrid, footer) =====
    TITLE_COLOR = colors.HexColor("#4a4a4a")
    logo_path = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")
    try:
        if os.path.exists(logo_path):
            im = Image.open(logo_path)
            try: im = ImageOps.exif_transpose(im)
            except Exception: pass
            im = im.convert("RGB")
            bbox = im.getbbox()
            if bbox: im = im.crop(bbox)
            ir_logo = ImageReader(im)
            lw, lh = im.size
            logo_target_h = 3.8*cm
            scale = logo_target_h / lh
            logo_w = lw*scale; logo_h = lh*scale
            top_margin = 0.8*cm
            title_font = 16
            ascent_pts = 0.80 * title_font
            title_top_y = h - top_margin
            y_logo = title_top_y - logo_h
            c.drawImage(ir_logo, 2*cm, y_logo, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass
    c.setFillColor(TITLE_COLOR); c.setFont("Helvetica-Bold", 16)
    title_y = (h - 0.8*cm) - 0.80*16
    c.drawRightString(w-2*cm, title_y, "Opdrachtbon")
    c.setFont("Helvetica", 10); c.drawRightString(w-2*cm, title_y - 0.9*cm, now)
    
    def card(x, y, width, height, title):
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#d8e2ef"))
        c.setLineWidth(0.6)
        c.roundRect(x, y, width, height, 8, fill=1, stroke=1)
        c.setFillColor(TITLE_COLOR); c.setFont("Helvetica-Bold", 12)
        c.drawString(x+0.6*cm, y+height-0.55*cm, title)
    
    margin_x = 2*cm
    content_top = h - 6.8*cm
    col_w = w - 2*margin_x
    y = content_top
    
    data_h = 4.8*cm
    card(margin_x, y - data_h, col_w, data_h, "Klant & Voertuig")
    left_x = margin_x + 0.8*cm
    right_x = margin_x + col_w/2 + 0.2*cm
    line_y = y - 1.4*cm
    
    def draw_pair(x, y0, label, value):
        c.setFont("Helvetica-Bold", 10); c.setFillColor(TITLE_COLOR)
        c.drawString(x, y0, f"{label}:")
        c.setFont("Helvetica", 10); c.setFillColor(colors.black)
        c.drawString(x+3.2*cm, y0, value or "-")
    
    draw_pair(left_x,  line_y + 0.0*cm, "Klantnaam", klantnaam)
    draw_pair(left_x,  line_y - 0.85*cm, "Kenteken", kenteken)
    draw_pair(left_x,  line_y - 1.70*cm, "Merk/Type", (merk or "") + ((" " + type_) if type_ else ""))
    draw_pair(right_x, line_y + 0.0*cm, "Bouwjaar", bouwjaar)
    draw_pair(right_x, line_y - 0.85*cm, "IMEI", imei)
    draw_pair(right_x, line_y - 1.70*cm, "VIN", vin)
    
    y -= (data_h + 0.5*cm)
    
    op_h = 3.6*cm
    card(margin_x, y - op_h, col_w, op_h, "Opmerkingen")
    c.setFont("Helvetica", 10); c.setFillColor(colors.black)
    t = c.beginText(margin_x+0.8*cm, y - 1.2*cm); t.setLeading(14)
    for line in (opmerkingen or "").splitlines()[:22]:
        t.textLine(line[:120])
    c.drawText(t)
    y -= (op_h + 0.5*cm)
    
    photos_h = 10.0*cm
    card(margin_x, y - photos_h, col_w, photos_h, "Foto's")
    inner_x = margin_x + 0.6*cm
    inner_y_top = y - 1.4*cm
    inner_w = col_w - 1.2*cm
    inner_h = photos_h - 2.1*cm
    cols = 2; rows = 2
    cell_w = inner_w / cols; cell_h = inner_h / rows
    
    label_map = {"foto_kenteken":"Kenteken", "foto_imei":"IMEI", "foto_chassis":"Chassis", "foto_extra1":"Extra"}
    prepared = []
    for key, img_bytes, orig in fotos[:4]:
        small = _shrink_for_pdf(img_bytes, max_side=1200, target_kb=220)
        prepared.append((key, small, orig))
    
    from io import BytesIO as _B
    for i, tup in enumerate(prepared):
        key, small, orig = tup
        r = i // cols; cc = i % cols
        cx = inner_x + cc*cell_w; cy = inner_y_top - r*cell_h
        c.setStrokeColor(colors.HexColor("#cfd9e6"))
        c.roundRect(cx+0.2*cm, cy - cell_h + 0.2*cm, cell_w-0.4*cm, cell_h-0.4*cm, 6, fill=0, stroke=1)
        pad_x = 0.45*cm; pad_y = 0.50*cm
        max_w = cell_w - 2*pad_x; max_h = cell_h - pad_y - 0.9*cm
        try:
            ir = ImageReader(_B(small))
            iw, ih = ir.getSize(); sc = min(max_w/iw, max_h/ih) if iw and ih else 1.0
            tw, th = iw*sc, ih*sc
            img_x = cx + (cell_w - tw)/2; img_y = cy - pad_y - th
            c.setStrokeColor(colors.HexColor("#dde6f2"))
            c.rect(cx+pad_x, cy - pad_y - max_h, max_w, max_h, stroke=1, fill=0)
            c.drawImage(ir, img_x, img_y, width=tw, height=th, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
        c.setFont("Helvetica", 9); c.setFillColor(TITLE_COLOR)
        label = label_map.get(key, key)
        if orig: label += f" · {orig}"
        c.drawCentredString(cx + cell_w/2, cy - cell_h + 0.45*cm, label[:70])
    
    c.setStrokeColor(colors.HexColor("#d9e3f1")); c.setLineWidth(0.8)
    c.line(margin_x, 2.15*cm, w - margin_x, 2.15*cm)
    c.setFont("Helvetica-Oblique", 9); c.setFillColor(colors.HexColor("#6b7c93"))
    c.drawCentredString(w/2, 1.55*cm, "IC-North Automotive · gegenereerd via webformulier")
    c.save()

    pdf_bytes = pdf_buf.getvalue(); filename = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
    admin_list = split_emails(os.getenv("RECEIVER_EMAIL"))
    recipients = [*admin_list, *( [klantemail] if klantemail else [] )]
    seen=set(); recipients=[x for x in recipients if not (x in seen or seen.add(x))]

    subject = os.getenv("MAIL_SUBJECT", "Opdrachtbon – {klantnaam} – {kenteken}").format(klantnaam=klantnaam or "", kenteken=kenteken or "")
    body = os.getenv("MAIL_BODY", "In de bijlage vind je de opdrachtbon (PDF).")
    if sender and recipients:
        try:
            msg = build_message(subject, body, sender, ", ".join(recipients), attachments=[(pdf_bytes, filename, "application/pdf")])
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
