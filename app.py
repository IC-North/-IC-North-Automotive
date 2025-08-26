import os
import datetime
from flask import Flask, render_template_string, request
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

app = Flask(__name__)

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = '''
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Opdrachtbon</title>
        <style>
            body { font-family: Arial; padding: 20px; background:#f8f9fa; }
            input, textarea, select { width: 100%; padding: 10px; margin: 5px 0; border:1px solid #ccc; border-radius:6px;}
            button { padding: 15px; background: #005BAC; color: white; border: none; border-radius:6px; width: 100%; font-size:16px;}
            h2 { color:#005BAC; }
            label { font-weight:bold; color:#333;}
        </style>
    </head>
    <body>
        <img src="/static/logo.png" alt="Logo" style="max-height:80px; display:block; margin:auto;">
        <h2 style="text-align:center;">Opdrachtbon formulier</h2>
        <p style="text-align:right;"><b>Datum & tijd:</b> {{now}}</p>
        <form action="/submit" method="post">
            <label>Klantnaam</label><input type="text" name="klantnaam" required>
            <label>Kenteken</label><input type="text" name="kenteken" required>
            <label>Chassisnummer (17 tekens)</label><input type="text" name="chassisnummer" pattern=".{17}" required>
            <label>IMEI / QR code</label><input type="text" name="imei">
            <label>Werkzaamheden</label>
            <select name="werkzaamheden">
                <option>Inbouw</option>
                <option>Ombouw</option>
                <option>Overbouw</option>
                <option>Uitbouw</option>
                <option>Servicecall</option>
            </select>
            <label>Opmerkingen</label><textarea name="opmerkingen"></textarea>
            <label>Foto 1</label><input type="file" name="foto1">
            <label>Foto 2</label><input type="file" name="foto2">
            <label>Foto 3</label><input type="file" name="foto3">
            <label>Klant email</label><input type="email" name="klantemail">
            <button type="submit">Verstuur opdrachtbon</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(html, now=now)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
