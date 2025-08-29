import os
import json
import datetime
import requests
from flask import Flask, render_template_string, request, jsonify

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
            body { font-family: Arial; padding: 20px; background: #f5f7fa; }
            input, textarea, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 6px; }
            button { padding: 12px; background: #007BFF; color: white; border: none; border-radius: 6px; width: 100%; }
            button:hover { background: #0056b3; }
            .error { color: red; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h2>Opdrachtbon formulier</h2>
        <p><b>Datum & tijd:</b> {{now}}</p>
        <form>
            <label>Kenteken</label>
            <input type="text" id="kenteken" name="kenteken" oninput="formatKenteken(this)" required>
            <div id="kentekenError" class="error"></div>

            <label>Merk / Type / Bouwjaar</label>
            <input type="text" id="autodata" readonly>

            <label>IMEI nummer</label>
            <input type="text" id="imei" name="imei">
            <button type="button" onclick="startScanner('imei')">📷 Scan IMEI</button>

            <label>Chassisnummer (VIN)</label>
            <input type="text" id="vin" name="vin" maxlength="17">
            <button type="button" onclick="startScanner('vin')">📷 Scan VIN</button>
        </form>

        <script src="https://unpkg.com/@zxing/library@latest"></script>
        <script>
            function formatKenteken(input) {
                let value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
                let patterns = [
                    /^([A-Z]{2})(\d{2})(\d{2})$/, 
                    /^(\d{2})(\d{2})([A-Z]{2})$/, 
                    /^(\d{2})([A-Z]{2})(\d{2})$/, 
                    /^([A-Z]{2})(\d{2})([A-Z]{2})$/, 
                    /^([A-Z]{2})([A-Z]{2})(\d{2})$/, 
                    /^(\d{2})([A-Z]{2})([A-Z]{2})$/, 
                    /^([A-Z]{2})(\d{3})([A-Z]{1})$/, 
                    /^([A-Z]{1})(\d{3})([A-Z]{2})$/
                ];

                let formatted = value;
                let valid = false;

                for (let p of patterns) {
                    if (p.test(value)) {
                        formatted = value.replace(p, (match, p1, p2, p3) => `${p1}-${p2}-${p3}`);
                        valid = true;
                        break;
                    }
                }

                input.value = formatted;
                document.getElementById("kentekenError").innerText = valid ? "" : "❌ Ongeldig kenteken";
            }

            function startScanner(fieldId) {
                const codeReader = new ZXing.BrowserMultiFormatReader();
                codeReader.decodeFromVideoDevice(undefined, 'video', (result, err) => {
                    if (result) {
                        document.getElementById(fieldId).value = result.text;
                        codeReader.reset();
                        document.getElementById("video").remove();
                    }
                });

                if (!document.getElementById("video")) {
                    let video = document.createElement("video");
                    video.id = "video";
                    video.style.width = "100%";
                    document.body.appendChild(video);
                }
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, now=now)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
