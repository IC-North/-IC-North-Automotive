import os
import datetime
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# RDW API functie
def get_car_data(kenteken):
    url = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kenteken.replace('-', '').upper()}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200 and resp.json():
            data = resp.json()[0]
            merk = data.get("merk", "Onbekend")
            handelsbenaming = data.get("handelsbenaming", "Onbekend")
            bouwjaar = data.get("datum_eerste_toelating", "Onbekend")
            if bouwjaar != "Onbekend":
                bouwjaar = bouwjaar[:4]
            return {"merk": merk, "type": handelsbenaming, "bouwjaar": bouwjaar}
    except Exception as e:
        print("RDW fout:", e)
    return {"merk": "Onbekend", "type": "Onbekend", "bouwjaar": "Onbekend"}

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = """
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Opdrachtbon</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f4f6f8; }
            .form-container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }
            h2 { text-align: center; color: #2c3e50; }
            label { font-weight: bold; margin-top: 10px; display: block; }
            input, textarea, select, button { width: 100%; padding: 10px; margin-top: 5px; border-radius: 5px; border: 1px solid #ccc; }
            button { background: #007BFF; color: white; border: none; font-size: 16px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .scan-btn { background: #28a745; margin-top: 5px; }
            .scan-btn:hover { background: #1e7e34; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>Opdrachtbon</h2>
            <p><b>Datum & tijd:</b> {{now}}</p>
            <form action="/submit" method="post">
                <label>Klantnaam</label><input type="text" name="klantnaam" required>

                <label>Kenteken</label><input type="text" id="kenteken" name="kenteken" required>
                <button type="button" onclick="haalRDW()">Haal voertuiggegevens op</button>
                <p id="rdwResult"></p>

                <label>IMEI nummer</label><input type="text" id="imei" name="imei">
                <button type="button" class="scan-btn" onclick="startScan('imei')">Scan IMEI</button>

                <label>Chassisnummer (VIN)</label><input type="text" id="vin" name="vin" maxlength="17">
                <button type="button" class="scan-btn" onclick="startScan('vin')">Scan VIN</button>

                <label>Werkzaamheden</label>
                <select name="werkzaamheden">
                    <option>Inbouw</option>
                    <option>Ombouw</option>
                    <option>Overbouw</option>
                    <option>Uitbouw</option>
                    <option>Servicecall</option>
                </select>

                <label>Opmerkingen</label><textarea name="opmerkingen"></textarea>

                <label>Klant email</label><input type="email" name="klantemail">

                <button type="submit">Verstuur opdrachtbon</button>
            </form>
        </div>

        <script>
            function haalRDW() {
                let kenteken = document.getElementById("kenteken").value;
                fetch("/rdw/" + kenteken)
                .then(r => r.json())
                .then(data => {
                    document.getElementById("rdwResult").innerText =
                        "Merk: " + data.merk + ", Type: " + data.type + ", Bouwjaar: " + data.bouwjaar;
                });
            }

            function startScan(fieldId) {
                Quagga.init({
                    inputStream: { type: "LiveStream", constraints: { facingMode: "environment" } },
                    decoder: { readers: ["code_128_reader", "ean_reader", "ean_8_reader", "code_39_reader", "upc_reader", "upc_e_reader"] }
                }, function(err) {
                    if (err) { alert("Fout bij starten scanner: " + err); return; }
                    Quagga.start();
                });

                Quagga.onDetected(function(result) {
                    document.getElementById(fieldId).value = result.codeResult.code;
                    Quagga.stop();
                });
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html, now=now)

@app.route("/rdw/<kenteken>")
def rdw_lookup(kenteken):
    return jsonify(get_car_data(kenteken))

@app.route("/submit", methods=["POST"])
def submit():
    return "Opdrachtbon succesvol verstuurd! (Mock)"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
