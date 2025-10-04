
import re, requests
def format_kenteken(raw: str) -> str:
    k = re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()
    if len(k) == 6: return f"{k[:2]}-{k[2:4]}-{k[4:]}"
    if len(k) == 7: return f"{k[:2]}-{k[2:5]}-{k[5:]}"
    return k

def rdw_lookup(raw: str):
    k = re.sub(r"[^A-Za-z0-9]", "", raw or "").upper()
    url = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
    r = requests.get(url, params={"kenteken": k}, timeout=8)
    data = r.json() if r.ok else []
    return data[0] if data else None
