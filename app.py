@app.get("/")
def index():
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    html = r"""
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
        <div><label>Klant e-mail</label><input type="email" name="klantemail" placeholder="klant@domein.nl"></div>
      </div>

      <div class="row row-2">
        <div><label>Eigen e-mail (afzender)</label><input name="senderemail" placeholder="noreply@jouwdomein.nl" required></div>
        <div><label>Interne e-mail(s)</label><input name="receiveremail" placeholder="werkplaats@jouwdomein.nl"></div>
      </div>

      <div class="row">
        <button class="btn" type="submit">Versturen</button>
      </div>
    </form>
  </div>
</div>

<script>
// Format kenteken on change
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
    """
    return render_template_string(html, now=now)
