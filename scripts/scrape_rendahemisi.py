import requests, time, random, os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd

STATIONS = [
    {"id": 4, "slug": "dki1-bundaran-hi",   "nama": "DKI1"},
    {"id": 5, "slug": "dki2-kelapa-gading", "nama": "DKI2"},
    {"id": 6, "slug": "dki3-jagakarsa",     "nama": "DKI3"},
    {"id": 7, "slug": "dki4-lubang-buaya",  "nama": "DKI4"},
    {"id": 8, "slug": "dki5-kebun-jeruk",   "nama": "DKI5"},
]
START = datetime(2022, 1, 13)
END   = datetime(2022, 12, 31)         # celah panel: Jan-Nov 2022
OUT   = "data/raw/ispu_hourly/rendahemisi_2022.csv"
BASE  = "https://rendahemisi.jakarta.go.id/ispu-detail"
HDRS  = {"User-Agent": "Mozilla/5.0 (research; academic use)",
         "Referer": "https://rendahemisi.jakarta.go.id/ispu"}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
done = set()
if os.path.exists(OUT):                  # resume otomatis
    prev = pd.read_csv(OUT)
    done = set(zip(prev.station_id, prev.tanggal))
    print(f"resume: {len(done)} stasiun-hari sudah ada")

rows, new = [], 0
dates = [START + timedelta(days=i) for i in range((END - START).days + 1)]
for st in STATIONS:
    for d in dates:
        key = (st["nama"], d.strftime("%Y-%m-%d"))
        if key in done: continue
        url = f"{BASE}/{st['id']}/{st['slug']}/{d.strftime('%d-%m-%Y')}"
        try:
            r = requests.get(url, headers=HDRS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print("ERR", st["nama"], d.date(), e); continue
        soup = BeautifulSoup(r.text, "html.parser")
        for tb in soup.find_all("table"):
            hd = [c.get_text(strip=True) for c in tb.find("tr").find_all(["th","td"])]
            if "Waktu" not in hd: continue
            for tr in tb.find_all("tr")[1:]:
                cells = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(cells) < len(hd): continue
                rec = dict(zip(hd, cells))
                rows.append({"tanggal": d.strftime("%Y-%m-%d"),
                             "jam": rec.get("Waktu"), "station_id": st["nama"],
                             "pm10": rec.get("PM 10"), "pm25": rec.get("PM 2.5"),
                             "so2": rec.get("SO2"), "co": rec.get("CO"),
                             "o3": rec.get("O3"), "no2": rec.get("NO2"),
                             "kategori": rec.get("Kategori")})
            break
        new += 1
        if new % 25 == 0:                # auto-save berkala
            df = pd.DataFrame(rows)
            df.to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
            rows = []; print(f"saved... ({new} halaman baru)")
        time.sleep(random.uniform(1.0, 2.0))   # sopan ke server

if rows:
    pd.DataFrame(rows).to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
print("selesai")