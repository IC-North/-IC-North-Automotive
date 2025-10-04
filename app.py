
from mailer import build_message, send_email, MailConfigError
import os, re, io, datetime, requests
from flask import Flask, render_template_string, request, jsonify, send_file

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

app = Flask(__name__)

def format_kenteken(raw: str) -> str:
    k = re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()
    if len(k) == 6:
        return f"{k[:2]}-{k[2:4]}-{k[4:]}"
    if len(k) == 7:
        return f"{k[:2]}-{k[2:5]}-{k[5:]}"
    return k

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
        merk = row.get("merk","")
        handels = row.get("handelsbenaming","")
        det = row.get("datum_eerste_toelating","")
        bouwjaar = det[:4] if det and len(det)>=4 else ""
        return jsonify({"success": True, "merk": merk, "type": handels, "bouwjaar": bouwjaar})
    except Exception as e:
        return jsonify({"success": False, "message": f"RDW fout: {e}"})

@app.get("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = \"\"\"
<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Opdrachtbon</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#f5f6f8;margin:0;padding:24px}
.wrap{max-width:860px;margin:0 auto}
.card{background:#fff;border-radius:14px;box-shadow:0 6px 24px rgba(0,0,0,.06);padding:20px}
.row{display:grid;gap:12px;margin-bottom:12px}
.row-2{grid-template-columns:1fr; } @media (min-width:680px){ .row-2{grid-template-columns:1fr 1fr} }
label{font-weight:600;font-size:14px;margin-bottom:6px;display:block}
input,select,textarea{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #e5e7eb;border-radius:10px;font-size:14px}
.btn{background:#0d63ff;color:#fff;border:none;border-radius:10px;padding:12px 16px;font-weight:700;cursor:pointer}
.actions{display:flex;gap:10px}
.hint{font-size:12px;color:#6b7280}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h2>Opdrachtbon</h2>
    <div class="hint">Datum &amp; tijd: <strong>{{now}}</strong></div>
    <form action="/submit" method="post">
      <div class="row row-2">
        <div>
          <label>Kenteken</label>
          <input id="kenteken" name="kenteken" placeholder="XX-999-X" required>
        </div>
        <div class="actions" style="align-items:flex-end">
          <button type="button" id="rdw-btn" class="btn">Haal RDW gegevens</button>
        </div>
      </div>

      <div class="row row-2">
        <div><label>Merk</label><input id="merk" name="merk" readonly></div>
        <div><label>Type (handelsbenaming)</label><input id="type" name="type" readonly></div>
      </div>

      <div class="row row-2">
        <div><label>Bouwjaar</label><input id="bouwjaar" name="bouwjaar" readonly></div>
        <div><label>Klant e‑mail</label><input type="email" name="klantemail" placeholder="klant@domein.nl"></div>
      </div>

      <div class="row row-2">
        <div><label>Eigen e‑mail (afzender)</label><input name="senderemail" placeholder="noreply@jouwdomein.nl" required></div>
        <div><label>Interne e‑mail(s)</label><input name="receiveremail" placeholder="werkplaats@jouwdomein.nl"></div>
      </div>

      <div class="row">
        <button class="btn" type="submit">Versturen</button>
      </div>
    </form>
  </div>
</div>

<script>
const kentekenEl = document.getElementById('kenteken');
if (kentekenEl) {
  kentekenEl.addEventListener('change', () => {
    const raw = kentekenEl.value || "";
    fetch('/format_kenteken', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ raw })
    })
    .then(r => r.json())
    .then(d => { if (d && d.formatted) kentekenEl.value = d.formatted; })
    .catch(()=>{});
  });
}

async function haalRdw() {
  const val = (kentekenEl && kentekenEl.value || '').trim();
  if (!val) { alert('Vul eerst een kenteken in.'); return; }
  try {
    const resp = await fetch('/rdw?kenteken=' + encodeURIComponent(val.replace(/[^A-Za-z0-9]/g,'')));
    const d = await resp.json();
    if (d && d.success) {
      document.getElementById('merk').value = d.merk || "";
      document.getElementById('type').value = d.type || "";
      document.getElementById('bouwjaar').value = d.bouwjaar || "";
    } else {
      alert(d && d.message ? d.message : 'Geen gegevens gevonden.');
    }
  } catch(e) { alert('Fout bij RDW ophalen.'); }
}
document.getElementById('rdw-btn').addEventListener('click', (e)=>{ e.preventDefault(); haalRdw(); });
</script>
</body>
</html>
    \"\"\"
    return render_template_string(html, now=now)

@app.post("/submit")
def submit():
    form = request.form
    kenteken = format_kenteken(form.get("kenteken",""))
    merk = form.get("merk",""); vtype = form.get("type",""); bouwjaar = form.get("bouwjaar","")
    klantemail = (form.get("klantemail") or "").strip()
    sender = (form.get("senderemail") or os.getenv("SENDER_EMAIL") or "").strip()
    admin_list = (form.get("receiveremail") or os.getenv("RECEIVER_EMAIL") or "").strip()

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 2*cm
    c.setFont("Helvetica-Bold", 16); c.drawString(2*cm, y, "Opdrachtbon"); y -= 1*cm
    c.setFont("Helvetica", 12)
    lines = [
        f"Datum/tijd: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}",
        f"Kenteken: {kenteken}",
        f"Merk: {merk}",
        f"Type: {vtype}",
        f"Bouwjaar: {bouwjaar}",
    ]
    for line in lines:
        c.drawString(2*cm, y, line); y -= 0.7*cm
    c.showPage(); c.save()
    pdf_bytes = buf.getvalue()
    filename = f\"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf\"

    recipients = []
    if admin_list:
        for part in admin_list.replace(\";\",\",\").split(\",\"):
            if \"@\" in part: recipients.append(part.strip())
    if klantemail and \"@\" in klantemail:
        recipients.append(klantemail)
    seen=set(); recipients=[x for x in recipients if not (x in seen or seen.add(x))]

    if sender and recipients:
        subject = os.getenv(\"MAIL_SUBJECT\", \"Opdrachtbon – {kenteken}\").format(kenteken=kenteken or \"\")
        body = os.getenv(\"MAIL_BODY\", \"In de bijlage vind je de opdrachtbon (PDF).\");
        try:
            msg = build_message(subject, body, sender, \", \".join(recipients), attachments=[(pdf_bytes, filename, \"application/pdf\")])
            if klantemail:
                msg['Reply-To'] = klantemail
            status = send_email(msg)
            print(\"[mail] ok:\", status)
        except Exception as e:
            print(\"[mail][error]\", e)

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename, mimetype=\"application/pdf\")

@app.get(\"/mail_test\")
def mail_test():
    to = request.args.get(\"to\") or os.getenv(\"RECEIVER_EMAIL\") or os.getenv(\"SENDER_EMAIL\")
    sender = os.getenv(\"SENDER_EMAIL\") or \"\"
    if not to or not sender:
        return jsonify({\"ok\": False, \"error\": \"SENDER_EMAIL of ontvanger ontbreekt (?to=... of RECEIVER_EMAIL zetten).\"}), 400
    try:
        msg = build_message(\"Testmail – Opdrachtbon\", \"Dit is een test om te verifiëren dat SendGrid werkt.\", sender, to)
        status = send_email(msg)
        return jsonify({\"ok\": True, \"status\": status}), 200
    except Exception as e:
        return jsonify({\"ok\": False, \"error\": str(e)}), 500

@app.get(\"/healthz\")
def healthz(): return \"ok\", 200

if __name__ == \"__main__\":
    app.run(host=\"0.0.0.0\", port=int(os.environ.get(\"PORT\", \"5000\")), debug=False)
