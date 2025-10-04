from mailer import build_message, send_email, MailConfigError
import os, re, io, datetime, requests
from flask import Flask, request, jsonify, send_file, render_template_string
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
    w,h=A4; y=h-2*cm
    c.setFont("Helvetica-Bold",16); c.drawString(2*cm,y,"Opdrachtbon"); y-=1*cm
    for line in [kenteken, merk, vtype, bouwjaar]:
        c.drawString(2*cm,y,line); y-=0.7*cm
    c.showPage(); c.save()
    pdf_bytes = buf.getvalue()
    filename = f"opdrachtbon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    recipients = []
    if admin_list:
        for part in admin_list.replace(';',',').split(','):
            if '@' in part: recipients.append(part.strip())
    if klantemail and '@' in klantemail:
        recipients.append(klantemail)
    seen=set(); recipients=[x for x in recipients if not (x in seen or seen.add(x))]

    if sender and recipients:
        subject = os.getenv("MAIL_SUBJECT", f"Opdrachtbon – {kenteken}")
        body = os.getenv("MAIL_BODY", "In de bijlage vind je de opdrachtbon (PDF).")
        try:
            msg = build_message(subject, body, sender, ", ".join(recipients),
                attachments=[(pdf_bytes, filename, "application/pdf")])
            if klantemail:
                msg['Reply-To'] = klantemail
            status = send_email(msg)
            print("[mail] ok:", status)
        except Exception as e:
            print("[mail][error]", e)

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

@app.get("/mail_test")
def mail_test():
    to = request.args.get("to") or os.getenv("RECEIVER_EMAIL") or os.getenv("SENDER_EMAIL")
    sender = os.getenv("SENDER_EMAIL") or ""
    if not to or not sender:
        return jsonify({"ok": False, "error": "SENDER_EMAIL of ontvanger ontbreekt"}),400
    try:
        msg = build_message("Testmail – Opdrachtbon", "Dit is een test", sender, to)
        status = send_email(msg)
        return jsonify({"ok": True, "status": status}),200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}),500

@app.get("/healthz")
def healthz(): return "ok",200

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT","5000")), debug=False)
