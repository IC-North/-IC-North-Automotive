import os
import datetime
import requests
from flask import Flask, render_template_string, request

app = Flask(__name__)

# RDW API (kenteken info)
def get_rdw_info(kenteken):
    try:
        url = f"https://opendata.rdw.nl/api/records/1.0/search/?dataset=gekentekende_voertuigen&q=kenteken:{kenteken}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data["nhits"] > 0:
            record = data["records"][0]["fields"]
            merk = record.get("merk", "Onbekend")
            handelsbenaming = record.get("handelsbenaming", "Onbekend")
            bouwjaar = record.get("datum_eerste_toelating", "Onbekend")[:4]
            return merk, handelsbenaming, bouwjaar
    except Exception as e:
        print("RDW fout:", e)
    return "Onbekend", "Onbekend", "Onbekend"


@app.route("/", methods=["GET", "POST"])
def index():
    merk = type_auto = bouwjaar = ""
    if request.method == "POST":
        kenteken = request.form.get("kenteken", "").replace("-", "").upper()
        imei = request.form.get("imei")
        chassis = request.form.get("chassis")
        opmerkingen = request.form.get("opmerkingen")
        merk, type_auto, bouwjaar = get_rdw_info(kenteken)
    else:
        kenteken = imei = chassis = opmerkingen = ""

    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>IC-North Automotive - Opdrachtbon</title>
      <style>
        body {{ font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 20px; background: #f7f9fb; }}
        h2 {{ text-align: center; color: #003366; }}
        label {{ font-weight: bold; display:block; margin-top: 10px; }}
        input, textarea {{ width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 6px; }}
        button {{ margin-top: 15px; padding: 15px; background: #003366; color: white; border: none; border-radius: 8px; width: 100%; }}
        #scanner {{ width: 100%; height: 250px; background: #000; margin-top: 10px; }}
      </style>
    </head>
    <body>
      <h2>IC-North Automotive<br>Opdrachtbon</h2>
      <p><b>Datum & tijd:</b> {now}</p>
      <form method="POST">
        <label>Kenteken</label>
        <input type="text" name="kenteken" value="{kenteken}" onblur="this.form.submit()" required>
        <p><b>Merk:</b> {merk} | <b>Type:</b> {type_auto} | <b>Bouwjaar:</b> {bouwjaar}</p>

        <label>IMEI nummer</label>
        <input type="text" id="imei" name="imei" value="{imei}">
        <button type="button" onclick="startBarcodeScanner()">Scan IMEI (Barcode/QR)</button>
        <div id="scanner"></div>

        <label>Chassisnummer (17 tekens)</label>
        <input type="text" id="chassis" name="chassis" value="{chassis}" maxlength="17">

        <label>Opmerkingen</label>
        <textarea name="opmerkingen">{opmerkingen}</textarea>

        <button type="submit">Verstuur</button>
      </form>

      <!-- QuaggaJS (Barcode scanner) -->
      <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
      <!-- jsQR (QR scanner) -->
      <script src="https://cdn.jsdelivr.net/npm/jsqr/dist/jsQR.js"></script>

      <script>
        function startBarcodeScanner() {{
          Quagga.init({{
            inputStream: {{
              name: "Live",
              type: "LiveStream",
              target: document.querySelector('#scanner'),
              constraints: {{
                facingMode: "environment"
              }}
            }},
            decoder: {{
              readers: ["code_128_reader","ean_reader","ean_8_reader","code_39_reader"]
            }}
          }}, function(err) {{
            if (err) {{
              console.log(err);
              alert("Fout bij starten scanner: " + err);
              return;
            }}
            Quagga.start();
          }});

          Quagga.onDetected(function(result) {{
            document.getElementById("imei").value = result.codeResult.code;
            Quagga.stop();
            alert("IMEI gescand: " + result.codeResult.code);
          }});
        }}
      </script>
    </body>
    </html>
    """
    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
