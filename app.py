import os
import datetime
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# RDW API
RDW_API = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"

@app.route("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = '''
    <!doctype html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Opdrachtbon</title>
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <style>
            body { font-family: Arial; padding: 20px; background:#f5f7fa; }
            .form-container { max-width: 600px; margin: auto; background:white; padding:20px; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1); }
            input, textarea, select { width: 100%; padding: 10px; margin: 5px 0; border:1px solid #ccc; border-radius:5px; }
            button { padding: 10px; background: #004080; color: white; border: none; border-radius:5px; cursor:pointer; width:100%; }
            button:hover { background: #0066cc; }
            .scanner { width:100%; margin:10px 0; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>Opdrachtbon</h2>
            <p><b>Datum & tijd:</b> {{now}}</p>
            <form>
                <label>Klantnaam</label><input type="text" name="klantnaam" required>
                <label>Kenteken</label><input type="text" id="kenteken" name="kenteken" required>
                <button type="button" onclick="haalRDW()">Haal voertuig info op</button>
                <label>Merk</label><input type="text" id="merk" readonly>
                <label>Type</label><input type="text" id="handelsbenaming" readonly>
                <label>Bouwjaar</label><input type="text" id="bouwjaar" readonly>

                <label>IMEI nummer</label>
                <input type="text" id="imei" name="imei">
                <button type="button" onclick="startScanner('imei')">📷 Scan IMEI</button>
                <div id="reader-imei" class="scanner"></div>

                <label>Chassisnummer (VIN)</label>
                <input type="text" id="vin" name="vin" maxlength="17">
                <button type="button" onclick="startScanner('vin')">📷 Scan VIN</button>
                <div id="reader-vin" class="scanner"></div>

                <label>Werkzaamheden</label>
                <select name="werkzaamheden">
                    <option>Inbouw</option>
                    <option>Ombouw</option>
                    <option>Overbouw</option>
                    <option>Uitbouw</option>
                    <option>Servicecall</option>
                </select>
                <label>Opmerkingen</label><textarea name="opmerkingen"></textarea>
                <button type="submit">Verstuur opdrachtbon</button>
            </form>
        </div>

        <script>
        function haalRDW(){
            let kenteken = document.getElementById("kenteken").value.replace(/-/g, "");
            fetch("/rdw/" + kenteken)
            .then(res => res.json())
            .then(data => {
                if(data.error){ alert("Niet gevonden"); return; }
                document.getElementById("merk").value = data.merk;
                document.getElementById("handelsbenaming").value = data.type;
                document.getElementById("bouwjaar").value = data.bouwjaar;
            });
        }

        function startScanner(field){
            let readerId = "reader-" + field;
            let inputId = field;
            let html5QrcodeScanner = new Html5Qrcode(readerId);
            html5QrcodeScanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                (decodedText) => {
                    document.getElementById(inputId).value = decodedText;
                    html5QrcodeScanner.stop();
                    document.getElementById(readerId).innerHTML = "";
                },
                (errorMessage) => {}
            ).catch(err => { alert("Camera fout: " + err); });
        }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, now=now)

@app.route("/rdw/<kenteken>")
def rdw_lookup(kenteken):
    try:
        r = requests.get(RDW_API, params={"kenteken": kenteken.upper()})
        data = r.json()
        if not data:
            return jsonify({"error": "Niet gevonden"})
        voertuig = data[0]
        return jsonify({
            "merk": voertuig.get("merk", ""),
            "type": voertuig.get("handelsbenaming", ""),
            "bouwjaar": voertuig.get("datum_eerste_toelating", "")[:4]
        })
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
