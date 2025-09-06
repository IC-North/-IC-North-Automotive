from mailer import build_message, send_email, MailConfigError\nimport os\n
import os
import re
import json
import datetime
import requests
from io import BytesIO
from flask import Flask, render_template_string, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

app = Flask(__name__)

# ---------- Helpers ----------
def format_kenteken(raw: str) -> str:
    """Zet kenteken om naar hoofdletters en plaats streepjes tussen letter-/cijferblokken.
    Voorbeeld: 'vgk91x' -> 'VGK-91-X'  |  '12ab34' -> '12-AB-34'"""
    if not raw:
        return ""
    s = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    parts = re.findall(r"[A-Z]+|\d+", s)
    return "-".join(parts)

def safe_get(d, key, default=""):
    return d.get(key, default) if isinstance(d, dict) else default

# ---------- Routes ----------
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
        .hint{ font-size:12px; color:var(--muted); margin-top:-10px; margin-bottom:10px }
        .scanner{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:50; align-items:center; justify-content:center; }
        .scanner .box{ background:#0b1220; border-radius:16px; width:min(92vw,620px); padding:12px }
        .scanner header{ color:#cbd5e1; padding:6px 8px 10px; display:flex; justify-content:space-between; align-items:center }
        .scanner button{ background:#111827; color:#fff; border:0; border-radius:10px; padding:8px 12px; cursor:pointer }
        .rdw{ display:flex; gap:10px; align-items:end }
        .rdw button{ white-space:nowrap }
        .footer-info{ color:#9ca3af; font-size:12px; text-align:center; margin-top:8px }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="card">
          <h1>Opdrachtbon</h1>
          <div class="sub">Datum &amp; tijd: <strong>{{now}}</strong></div>

          <form action="/submit" method="post" id="bonform">
            <div class="row row-2">
              <div>
                <label>Klantnaam</label>
                <input name="klantnaam" required placeholder="Bedrijf of persoon">
              </div>
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
              <div>
                <label>Merk</label>
                <input id="merk" name="merk" readonly>
              </div>
              <div>
                <label>Type</label>
                <input id="type" name="type" readonly>
              </div>
              <div>
                <label>Bouwjaar</label>
                <input id="bouwjaar" name="bouwjaar" readonly>
              </div>
            </div>

            <div class="row row-2">
              <div>
                <label>IMEI nummer</label>
                <input id="imei" name="imei" placeholder="Scan of typ het nummer">
                <div class="actions">
                  <button type="button" class="btn icon" onclick="openScanner('imei')">Scan IMEI</button>
                </div>
              </div>
              <div>
                <label>VIN (chassisnummer – 17 tekens)</label>
                <input id="vin" name="vin" maxlength="17" minlength="17" placeholder="Scan of typ VIN (17)">
                <div class="actions">
                  <button type="button" class="btn icon" onclick="openScanner('vin')">Scan VIN</button>
                </div>
              </div>
            </div>

            <div>
              <label>Werkzaamheden</label>
              <select name="werkzaamheden">
                <option>Inbouw</option>
                <option>Ombouw</option>
                <option>Overbouw</option>
                <option>Uitbouw</option>
                <option>Servicecall</option>
              </select>
            </div>

            <div>
              <label>Opmerkingen</label>
              <textarea name="opmerkingen" placeholder="Toelichting op uitgevoerde werkzaamheden"></textarea>
            </div>

            <div class="row row-2">
              <div>
                <label>Klant e‑mail</label>
                <input type="email" name="klantemail" placeholder="klant@domein.nl">
              </div>
              <div>
                <label>Eigen e‑mail (afzender)</label>
                <input type="email" name="senderemail" placeholder="icnorthautomotive@gmail.com" value="icnorthautomotive@gmail.com">
              </div>
            </div>

            <button class="btn" type="submit">PDF maken &amp; mailen</button>
          </form>

          <div class="footer-info">Scan werkt op iPhone (Safari) via camera &nbsp;•&nbsp; RDW via open data</div>
        </div>
      </div>

      <!-- Scanner modal -->
      <div class="scanner" id="scanner">
        <div class="box">
          <header>
            <div>Camera scanner</div>
            <button onclick="closeScanner()">Sluiten</button>
          </header>
          <div id="reader" style="width:100%;"></div>
        </div>
      </div>

      <script>
        // Kenteken automatisch formatteren
        const kentekenEl = document.getElementById('kenteken');
        kentekenEl.addEventListener('change', () => {
          const raw = kentekenEl.value;
          fetch('/format_kenteken', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({raw})})
            .then(r=>r.json()).then(d=>{ kentekenEl.value = d.formatted; });
        });

        // RDW halen
        function haalRdw(){
          const k = kentekenEl.value.trim();
          if(!k){ alert('Vul eerst een kenteken in.'); return; }
          fetch('/rdw?kenteken='+encodeURIComponent(k))
            .then(r=>r.json()).then(d=>{
              if(d && d.success){
                document.getElementById('merk').value = d.merk || '';
                document.getElementById('type').value = d.type || '';
                document.getElementById('bouwjaar').value = d.bouwjaar || '';
              } else {
                alert(d.message || 'Geen gegevens gevonden.');
              }
            }).catch(()=>alert('Fout bij RDW ophalen.'));
        }

        // Scanner (html5-qrcode)
        let currentTarget = null;
        let html5Scanner = null;

        function openScanner(target){
          currentTarget = target;
          document.getElementById('scanner').style.display = 'flex';

          const qrConfig = { fps: 10, qrbox: 240, rememberLastUsedCamera: true, formatsToSupport: [ Html5QrcodeSupportedFormats.QR_CODE, Html5QrcodeSupportedFormats.CODE_39, Html5QrcodeSupportedFormats.CODE_128, Html5QrcodeSupportedFormats.EAN_13, Html5QrcodeSupportedFormats.EAN_8 ] };

          html5Scanner = new Html5Qrcode("reader");
          html5Scanner.start(
            { facingMode: "environment" },
            qrConfig,
            (decodedText, decodedResult) => {
              // VIN barcodes zijn vaak CODE_39 (zonder I/O/Q) — filter op 17 tekens voor VIN
              if(currentTarget === 'vin'){
                const cleaned = decodedText.replace(/[^A-Za-z0-9]/g,'').toUpperCase();
                // VIN mag geen I, O, Q bevatten
                const vin = cleaned.replace(/[IOQ]/g, '');
                if(vin.length === 17){
                  document.getElementById('vin').value = vin;
                  closeScanner();
                }
              } else if(currentTarget === 'imei'){
                const imei = decodedText.replace(/[^0-9]/g,'');
                if(imei.length >= 14){ // 14 or 15 digits for IMEI
                  document.getElementById('imei').value = imei;
                  closeScanner();
                }
              }
            },
            (errorMessage) => { /* ignore scan errors for performance */ }
          ).catch(err => {
            alert("Kon de camera niet starten: " + err);
            closeScanner();
          });
        }

        function closeScanner(){
          document.getElementById('scanner').style.display = 'none';
          if(html5Scanner){
            html5Scanner.stop().then(() => {
              html5Scanner.clear();
              html5Scanner = null;
            }).catch(() => {});
          }
        }
      </script>
    
<script>
function formatKenteken() {
    let input = document.getElementById("kenteken");
    let val = input.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (val.length === 6) {
        val = val.replace(/(.{2})(.{2})(.{2})/, "$1-$2-$3");
    } else if (val.length === 7) {
        val = val.replace(/(.{2})(.{3})(.{2})/, "$1-$2-$3");
    } else if (val.length === 8) {
        val = val.replace(/(.{2})(.{2})(.{3})(.{1})/, "$1-$2-$3-$4");
    }
    input.value = val;
}
</script>

</body>
    </html>
    """
    return render_template_string(html, now=now)

@app.route("/format_kenteken", methods=["POST"])
def api_format_kenteken():
    data = request.get_json(force=True, silent=True) or {}
    formatted = format_kenteken(data.get("raw",""))
    return jsonify({"formatted": formatted})

@app.route("/rdw")
def rdw():
    raw = request.args.get("kenteken","")
    k = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if not k:
        return jsonify({"success": False, "message": "Geen kenteken opgegeven."})
    try:
        # RDW open data: basisgegevens voertuigen
        url = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
        resp = requests.get(url, params={"kenteken": k}, timeout=8)
        data = resp.json() if resp.ok else []
        if not data:
            return jsonify({"success": False, "message": "Kenteken niet gevonden bij RDW."})
        row = data[0]
        merk = row.get("merk","")
        handels = row.get("handelsbenaming","")
        # Datum eerste toelating kan 'YYYYMMDD' zijn
        det = row.get("datum_eerste_toelating","")
        bouwjaar = det[:4] if det and len(det)>=4 else ""
        return jsonify({"success": True, "merk": merk, "type": handels, "bouwjaar": bouwjaar})
    except Exception as e:
        return jsonify({"success": False, "message": f"RDW fout: {e}"})

@app.route("/submit", methods=["POST"])
def submit():
    klantnaam = request.form.get("klantnaam","")
    kenteken = format_kenteken(request.form.get("kenteken",""))
    merk = request.form.get("merk","")
    type_ = request.form.get("type","")
    bouwjaar = request.form.get("bouwjaar","")
    imei = request.form.get("imei","")
    vin = request.form.get("vin","")
    werkzaamheden = request.form.get("werkzaamheden","")
    opmerkingen = request.form.get("opmerkingen","")
    klantemail = request.form.get("klantemail","")
    senderemail = request.form.get("senderemail","icnorthautomotive@gmail.com")

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    # Maak PDF (alleen voorbeeld, mailen kan apart worden geconfigureerd)
    pdf_buf = BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 13)
    c.drawString(2*cm, height-2*cm, f"Opdrachtbon · {now}")

    c.setFont("Helvetica", 11)
    y = height-3.2*cm
    lines = [
        f"Klantnaam: {klantnaam}",
        f"Kenteken: {kenteken}  |  Merk: {merk}  |  Type: {type_}  |  Bouwjaar: {bouwjaar}",
        f"IMEI: {imei}",
        f"VIN: {vin}",
        f"Werkzaamheden: {werkzaamheden}",
    ]
    for ln in lines:
        c.drawString(2*cm, y, ln); y -= 1.0*cm

    # Opmerkingen blok
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2*cm, y, "Opmerkingen:"); y -= 0.6*cm
    c.setFont("Helvetica", 10)
    textobj = c.beginText(2*cm, y)
    for para_line in opmerkingen.splitlines() or ["-"]:
        textobj.textLine(para_line)
    c.drawText(textobj)

    c.setFillColor(colors.grey)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2*cm, 1.5*cm, "IC‑North Automotive · gegenereerd via webformulier")
    c.save()

    
    # --- E-mail verzenden (optioneel) ---
    # Gebruik de afzender uit het formulier als gebruikersnaam; wachtwoord via env SMTP_PASSWORD (Gmail app-wachtwoord aanbevolen).
    senderemail = (request.form.get("senderemail") or "").strip()
    klantemail = (request.form.get("klantemail") or "").strip()
    admin_bcc = os.environ.get("RECEIVER_EMAIL", "").strip()
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    subject_text = os.environ.get("MAIL_SUBJECT", "Opdrachtbon – {klantnaam} – {kenteken}").format(klantnaam=klantnaam or "", kenteken=kenteken or "")
    body_text = os.environ.get("MAIL_BODY", "In de bijlage vind je de opdrachtbon (PDF).")

    sent = False
    send_error = None
    tos = [e for e in [klantemail, admin_bcc] if e]

    if senderemail and smtp_password and tos:
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.application import MIMEApplication
            from email.mime.text import MIMEText
            import smtplib, socket
            socket.setdefaulttimeout(10)

            msg = MIMEMultipart()
            msg["From"] = senderemail
            msg["To"] = ", ".join(tos)
            msg["Subject"] = subject_text
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            part = MIMEApplication(pdf_buf.getvalue(), _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.starttls()
                s.login(senderemail, smtp_password)
                s.sendmail(senderemail, tos, msg.as_string())
            sent = True
        except Exception as e:
            send_error = str(e)

    # Download fallback en statusmelding
    pdf_buf.seek(0)
    filename = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    if sent:
        # Laat ook download toe, met melding in bestandsnaam
        return send_file(pdf_buf, as_attachment=True, download_name=filename, mimetype="application/pdf")
    elif send_error:
        # Stuur bestand toch terug, met foutmelding in bestandsnaam
        fail_name = filename.replace(".pdf", "_MAIL_FOUT.pdf")
        return send_file(pdf_buf, as_attachment=True, download_name=fail_name, mimetype="application/pdf")
    else:
        # Geen e-mailconfig of ontvangers: alleen download
        return send_file(pdf_buf, as_attachment=True, download_name=filename, mimetype="application/pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


@app.get("/healthz")
def healthz():
    return "ok", 200


@app.get("/debug/send-test")
def send_test():
    sender = os.getenv("SENDER_EMAIL") or os.getenv("SMTP_USER")
    rcpt   = os.getenv("RECEIVER_EMAIL") or sender
    msg = build_message(
        subject="Test IC-North mail",
        body_text="Dit is een test vanaf Render.",
        sender=sender,
        recipient=rcpt
    )
    status = send_email(msg)
    return {"ok": True, "status": status}
