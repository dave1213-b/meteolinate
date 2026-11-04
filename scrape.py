import re, json, html, urllib.request, datetime, sys

URL = "https://retemeteolombardia.altervista.org/linate/station.htm"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (meteo-mirror)"})
raw = urllib.request.urlopen(req, timeout=30).read().decode("cp1252", "replace")
t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
t = re.sub(r"<[^>]+>", " ", t)
t = html.unescape(t).replace("\ufffd", "°")
t = re.sub(r"\s+", " ", t)

N = r"(-?\d+(?:\.\d+)?)"
def g(p, s):
    m = re.search(p, s)
    return m.group(1) if m else None

order = [("temp", "TEMPERATURA"), ("hum", "UMIDIT"), ("dew", "DEW POINT"), ("press", "PRESSIONE"),
         ("rain", "PRECIPITAZIONI"), ("rate", "INTENSIT"), ("heat", "INDICE DI CALORE"),
         ("wind", "VENTO"), ("chill", "WIND CHILL"), ("end", "SPECIFICHE")]
pos, p = [], 0
for k, h in order:
    i = t.find(h, p)
    pos.append((k, i, h))
    if i >= 0:
        p = i
secs = {}
for n, (k, i, h) in enumerate(pos[:-1]):
    nxt = next((j for _, j, _ in pos[n + 1:] if j > i), len(t))
    if i >= 0:
        secs[k] = t[i + len(h):nxt]

def generic(s):
    d = {"now": g(N, s)}
    for key, lab in (("max", "Max oggi:"), ("min", "Min oggi:")):
        m = re.search(lab + r"\s*" + N + r"\D*?(\d{1,2}:\d{2})", s)
        if m:
            d[key], d[key + "T"] = m.group(1), m.group(2)
    mese = re.findall(r"Mese:\s*" + N, s)
    anno = re.findall(r"Anno:\s*" + N, s)
    if len(mese) > 0: d["mMax"] = mese[0]
    if len(mese) > 1: d["mMin"] = mese[1]
    if len(anno) > 0: d["yMax"] = anno[0]
    if len(anno) > 1: d["yMin"] = anno[1]
    return d

data = {k: generic(secs[k]) for k in ("temp", "hum", "dew", "press", "heat", "chill") if k in secs}

r = secs.get("rain", "")
data["rain"] = {"now": g(N, r), "event": g(r"Perturbazione:\s*" + N, r),
                "month": g(r"Totale Mese:\s*" + N, r), "year": g(r"Totale Anno:\s*" + N, r)}
s = secs.get("rate", "")
data["rate"] = {"now": g(N, s), "max": g(r"Max oggi:\s*" + N, s),
                "hour": g(r"Max oraria:\s*" + N, s), "year": g(r"Anno:\s*" + N, s)}
w = secs.get("wind", "")
m = re.search(N + r"\s*km/h\s*([A-Z]{1,3})", w)
data["wind"] = {"now": m.group(1) if m else None, "dir": m.group(2) if m else None,
                "max": g(r"Max oggi:\s*" + N, w), "maxT": g(r"Max oggi:\s*" + N + r"\s*km/h\s*(\d{1,2}:\d{2})", w) and
                re.search(r"Max oggi:.*?(\d{1,2}:\d{2})", w).group(1),
                "avg": g(r"Media 10 min:\s*" + N, w),
                "gustM": g(r"Mese:\s*" + N, w), "gustY": g(r"Anno:\s*" + N, w)}

m = re.search(r"Dati registrati alle ore\s*(\d{1,2}:\d{2})\s*del giorno\s*(\S+)", t)
data["time"], data["date"] = (m.group(1), m.group(2)) if m else (None, None)
m = re.search(r"Alba:\s*(\d{1,2}:\d{2})\s*Tramonto:\s*(\d{1,2}:\d{2})", t)
data["sunrise"], data["sunset"] = (m.group(1), m.group(2)) if m else (None, None)
data["fetched"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

if not data.get("temp", {}).get("now"):
    print("Parsing fallito, mantengo i dati vecchi")
    sys.exit(1)

json.dump(data, open("data.json", "w"), ensure_ascii=False, indent=1)
print("OK", data["time"], data["temp"]["now"])
