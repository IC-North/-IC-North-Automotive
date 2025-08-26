import os
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
            body { font-family: Arial; padding: 20px; background: #f4f7fb; }
            input, textarea, select, button { width: 100%; padding: 10px; margin: 5px 0; font-size: 16px; }
            button { background: #0056b3; color: white; border: none; cursor: pointer; }
            button:hover { background: #003d80; }
            .readonly { background: #e9ecef; }
        </style>
    </head>
    <body>
        <h2>Opdrachtbon formulier</h2>
        <p><b>Datum & tijd:</b> {{now}}</p>
        <form action="/submit" method="post">
            <label>Kenteken</label>
            <input type="text" id="kenteken" name="kenteken" required>
            <button type="button" onclick="haalGegevens()">Haal gegevens op</button>
            
            <label>Merk</label>
            <input type="text" id="merk" name="merk" class="readonly" readonly>
            
            <label>Type</label>
            <input type="text" id="handelsbenaming" name="handelsbenaming" class="readonly" readonly>
            
            <label>Bouwjaar</label>
            <input type="text" id="bouwjaar" name="bouwjaar" class="readonly" readonly>
            
            <label>Klantnaam</label><input type="text" name="klantnaam" required>
            <label>IMEI nummer (scan of invoer)</label><input type="text" name="imei">
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

        <script>
        async function haalGegevens() {
            const kenteken = document.getElementById("kenteken").value;
            if (!kenteken) { alert("Vul eerst een kenteken in"); return; }
            const response = await fetch(`/rdw/${kenteken}`);
            const data = await response.json();
            if (data.fout) {
                alert(data.fout);
            } else {
                document.getElementById("merk").value = data.merk;
                document.getElementById("handelsbenaming").value = data.handelsbenaming;
                document.getElementById("bouwjaar").value = data.bouwjaar;
            }
        }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html, now=now)

@app.route("/rdw/<kenteken>")
def rdw_lookup(kenteken):
    try:
        url = f"https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kenteken.replace('-','').upper()}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if not data:
            return jsonify({"fout": "Geen gegevens gevonden"})
        voertuig = data[0]
        return jsonify({
            "merk": voertuig.get("merk", ""),
            "handelsbenaming": voertuig.get("handelsbenaming", ""),
            "bouwjaar": voertuig.get("datum_eerste_toelating", "")[:4]
        })
    except Exception as e:
        return jsonify({"fout": str(e)})

@app.route("/submit", methods=["POST"])
def submit():
    return "Formulier verstuurd (demo)."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
