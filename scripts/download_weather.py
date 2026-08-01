import requests
import pandas as pd
from pathlib import Path
import time

OUT = Path("data/raw/weather")
OUT.mkdir(parents=True, exist_ok=True)

# Koordinat 5 SPKU — cukup akurat untuk data cuaca (grid Open-Meteo ~10 km).
# Nanti bisa diperbarui dengan koordinat presisi dari halaman Lokasi SPKU.
stations = {
    "DKI1_BundaranHI":   (-6.1946, 106.8230),
    "DKI2_KelapaGading": (-6.1530, 106.9080),
    "DKI3_Jagakarsa":    (-6.3350, 106.8200),
    "DKI4_LubangBuaya":  (-6.2900, 106.9040),
    "DKI5_KebonJeruk":   (-6.1970, 106.7740),
}

VARS = ("temperature_2m,relative_humidity_2m,precipitation,"
        "wind_speed_10m,wind_direction_10m")

for name, (lat, lon) in stations.items():
    print(f"Mengunduh {name} ...", end=" ", flush=True)
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": lat, "longitude": lon,
            "start_date": "2019-01-01",
            "end_date": "2026-07-28",
            "hourly": VARS,
            "timezone": "Asia/Jakarta",
        },
        timeout=120,
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    path = OUT / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"OK — {len(df):,} baris -> {path}")
    time.sleep(1)  # sopan ke server

print("\nSelesai. Verifikasi:")
for f in sorted(OUT.glob("*.csv")):
    d = pd.read_csv(f, usecols=["time"])
    print(f"  {f.name}: {d['time'].iloc[0]} s/d {d['time'].iloc[-1]}")