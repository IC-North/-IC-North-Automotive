
from flask import Blueprint, render_template, request, jsonify, send_file, flash
from .extensions import db
from .models import Customer, Vehicle, WorkOrder
from .rdw import rdw_lookup, format_kenteken
from .mailer import build_message, send_email
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import io, os, datetime

main_bp = Blueprint('main', __name__)

@main_bp.get('/')
def index():
    return render_template('form.html')

@main_bp.get('/rdw')
def rdw():
    kenteken = request.args.get('kenteken','')
    row = rdw_lookup(kenteken)
    if not row:
        return jsonify({"success": False, "message": "Kenteken niet gevonden bij RDW."})
    merk = row.get("merk",""); handels=row.get("handelsbenaming",""); det=row.get("datum_eerste_toelating","")
    bouwjaar = det[:4] if det and len(det)>=4 else ""
    return jsonify({"success": True, "merk": merk, "type": handels, "bouwjaar": bouwjaar})

@main_bp.post('/submit')
def submit():
    name = request.form.get('klantnaam') or ""
    klantemail = (request.form.get('klantemail') or "").strip()
    phone = request.form.get('telefoon') or ""
    kenteken_raw = request.form.get('kenteken') or ""
    brand = request.form.get('merk') or ""
    vtype = request.form.get('type') or ""
    bouwjaar = request.form.get('bouwjaar') or ""
    notes = request.form.get('opmerkingen') or ""
    sender = (request.form.get('senderemail') or os.getenv("SENDER_EMAIL") or "").strip()
    admin_list = (request.form.get('receiveremail') or os.getenv("RECEIVER_EMAIL") or "").strip()

    # Persist to DB
    cust = Customer(name=name, email=klantemail, phone=phone); db.session.add(cust)
    veh = Vehicle(license_plate=format_kenteken(kenteken_raw), brand=brand, model=vtype, year=bouwjaar); db.session.add(veh)
    db.session.flush()
    wo = WorkOrder(customer=cust, vehicle=veh, notes=notes); db.session.add(wo); db.session.commit()

    # Build PDF
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=A4); w,h=A4; y=h-2*cm
    c.setFont("Helvetica-Bold",16); c.drawString(2*cm,y,"Opdrachtbon"); y-=1*cm
    c.setFont("Helvetica",12)
    for line in [
        f"Datum/tijd: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}",
        f"Klant: {name}  |  Tel: {phone}",
        f"E-mail: {klantemail}",
        f"Kenteken: {format_kenteken(kenteken_raw)}",
        f"Merk/Type: {brand} / {vtype}",
        f"Bouwjaar: {bouwjaar}",
        f"Opmerkingen: {notes}",
        f"Bon ID: {wo.id}",
    ]:
        c.drawString(2*cm,y,line); y-=0.8*cm
    c.showPage(); c.save(); pdf_bytes = buf.getvalue()
    filename = f"opdrachtbon_{wo.id}.pdf"

    # Email
    recipients = []
    if admin_list:
        for part in admin_list.replace(';',',').split(','):
            if '@' in part: recipients.append(part.strip())
    if klantemail and '@' in klantemail: recipients.append(klantemail)
    seen=set(); recipients=[x for x in recipients if not (x in seen or seen.add(x))]

    if sender and recipients:
        subject = os.getenv("MAIL_SUBJECT", f"Opdrachtbon – {format_kenteken(kenteken_raw)} (#{wo.id})")
        body = os.getenv("MAIL_BODY", "In de bijlage vind je de opdrachtbon (PDF).")
        msg = build_message(subject, body, sender, ", ".join(recipients),
                            attachments=[(pdf_bytes, filename, "application/pdf")])
        if klantemail: msg['Reply-To'] = klantemail
        try:
            _status = send_email(msg)
        except Exception as e:
            flash(f"Mail versturen mislukte: {e}", "danger")

    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

@main_bp.get('/mail_test')
def mail_test():
    to = request.args.get('to') or os.getenv("RECEIVER_EMAIL") or os.getenv("SENDER_EMAIL")
    sender = os.getenv("SENDER_EMAIL") or ""
    if not to or not sender:
        return {"ok": False, "error": "SENDER_EMAIL of ontvanger ontbreekt"}, 400
    try:
        msg = build_message("Testmail – Opdrachtbon", "Dit is een test", sender, to)
        status = send_email(msg)
        return {"ok": True, "status": status}, 200
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500
