import os
import datetime
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Opdrachtbon</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: auto; }
    label { font-weight: bold; display:block; margin-top:10px; }
    input, textarea, select, button { width: 100%; padding: 10px; margin-top:5px; }
    button { background: #007BFF; color: white; border: none; cursor: pointer; }
    video { width: 100%; max-height: 250px; margin-top:10px; border:1px solid #ccc; display:none; }
  </style>
</head>
<body>
  <h2>Opdrachtbon formulier</h2>
  <form method="post" action="/submit">
    <label>Klantnaam</label>
    <input type="text" name="klantnaam" required>

    <label>Kenteken</label>
    <input type="text" id="kenteken" name="kenteken" required>
    <button type="button" onclick="haalRDW()">Check RDW gegevens</button>
    <p><b>Merk/Type/Bouwjaar:</b> <span id="rdw_result"></span></p>

    <label>IMEI nummer</label>
    <input type="text" id="imei" name="imei">
    <button type="button" onclick="startScanner('imei')">Scan IMEI</button>

    <label>Chassisnummer (VIN)</label>
    <input type="text" id="vin" name="vin" maxlength="17">
    <button type="button" onclick="startScanner('vin')">Scan VIN</button>

    <video id="preview"></video>

    <label>Werkzaamheden</label>
    <select name="werkzaamheden">
      <option>Inbouw</option>
      <option>Ombouw</option>
      <option>Overbouw</option>
      <option>Uitbouw</option>
      <option>Servicecall</option>
    </select>

    <label>Opmerkingen / Omschrijving</label>
    <textarea name="opmerkingen"></textarea>

    <label>Klant email</label>
    <input type="email" name="klantemail">

    <button type="submit">Verstuur opdrachtbon</button>
  </form>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/jsqr/1.4.0/jsQR.min.js"></script>
  <script>
    function formatKenteken(value) {
      value = value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      return value.match(/.{1,2}/g)?.join("-") || value;
    }

    document.getElementById("kenteken").addEventListener("input", function() {
      this.value = formatKenteken(this.value);
    });

    function haalRDW() {
      const kenteken = document.getElementById("kenteken").value.replace(/-/g, "");
      fetch(`/rdw/${kenteken}`)
        .then(res => res.json())
        .then(data => {
          if(data.error) {
            document.getElementById("rdw_result").innerText = "Niet gevonden";
          } else {
            document.getElementById("rdw_result").innerText = data.merk + " " + data.handelsbenaming + " (" + data.bouwjaar + ")";
          }
        });
    }

    let currentField = null;
    let video = document.getElementById("preview");
    let scanning = false;

    function startScanner(field) {
      currentField = field;
      navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } }).then(stream => {
        video.srcObject = stream;
        video.setAttribute("playsinline", true);
        video.play();
        video.style.display = "block";
        scanning = true;
        requestAnimationFrame(tick);
      });
    }

    function tick() {
      if (!scanning) return;
      let canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      let ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      let code = jsQR(imageData.data, canvas.width, canvas.height);
      if (code) {
        document.getElementById(currentField).value = code.data;
        stopScanner();
      } else {
        requestAnimationFrame(tick);
      }
    }

    function stopScanner() {
      scanning = false;
      video.style.display = "none";
      let stream = video.srcObject;
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_FORM)

@app.route("/rdw/<kenteken>")
def rdw_lookup(kenteken):
    url = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kenteken.upper()}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if not data:
            return jsonify({"error": "Geen data"})
        auto = data[0]
        bouwjaar = auto.get("datum_eerste_toelating", "")[:4]
        return jsonify({
            "merk": auto.get("merk", ""),
            "handelsbenaming": auto.get("handelsbenaming", ""),
            "bouwjaar": bouwjaar
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/submit", methods=["POST"])
def submit():
    return "Opdrachtbon succesvol ingediend!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def normalize_kenteken(kenteken: str) -> str:
    import re
    kenteken = kenteken.upper().replace(" ", "").replace("-", "")
    # Nederlands kenteken patroon (vereenvoudigd): 6/7 letters+cijfers met streepjes
    if len(kenteken) == 6:
        return f"{kenteken[0:2]}-{kenteken[2:4]}-{kenteken[4:6]}"
    elif len(kenteken) == 7:
        return f"{kenteken[0:2]}-{kenteken[2:3]}-{kenteken[3:6]}"
    return kenteken
