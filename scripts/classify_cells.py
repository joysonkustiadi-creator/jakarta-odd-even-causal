import pandas as pd, json, glob
import numpy as np
from shapely.geometry import LineString, box
import matplotlib.pyplot as plt

HALF = 3500 / 2 / 111320  # setengah sisi sel (derajat, ~aproks di ekuator)

# grid unik dari salah satu file TROPOMI
tro = pd.read_csv(sorted(glob.glob("data/raw/tropomi/*.csv"))[0])
cells = tro[["cell_id", "lon", "lat"]].drop_duplicates().reset_index(drop=True)

# ruas gage
gj = json.load(open("data/raw/geo/gage_roads_v0_approx.geojson"))
roads = [(f["properties"]["name"], f["properties"]["phase_13ruas_okt2021"],
          LineString(f["geometry"]["coordinates"])) for f in gj["features"]]

rows = []
for _, c in cells.iterrows():
    cell_poly = box(c.lon - HALF, c.lat - HALF, c.lon + HALF, c.lat + HALF)
    hit13 = any(cell_poly.intersects(g) for _, is13, g in roads if is13)
    hitnew = any(cell_poly.intersects(g) for _, is13, g in roads if not is13)
    dmin = min(cell_poly.distance(g) for *_ , g in roads) * 111.32  # km
    if hit13 and hitnew: grp = "treated_both"
    elif hit13:          grp = "treated_13ruas"
    elif hitnew:         grp = "treated_new12"
    elif dmin > 2.0:     grp = "control"
    else:                grp = "buffer_excluded"   # dekat tapi tak memotong
    rows.append({**c, "group": grp, "dist_km": round(dmin, 2)})

cl = pd.DataFrame(rows)
print(cl.group.value_counts())
cl.to_csv("data/processed/tropomi_cells_classified.csv", index=False)

# peta
colors = {"treated_both": "#b71c1c", "treated_13ruas": "#e65100",
          "treated_new12": "#f9a825", "control": "#2e7d32", "buffer_excluded": "#bdbdbd"}
fig, ax = plt.subplots(figsize=(10, 8))
for g, sub in cl.groupby("group"):
    ax.scatter(sub.lon, sub.lat, c=colors[g], s=90, marker="s", label=f"{g} ({len(sub)})")
for name, is13, geom in roads:
    x, y = geom.xy
    ax.plot(x, y, lw=2, color="#e65100" if is13 else "#f9a825")
ax.legend(fontsize=8); ax.set_title("Klasifikasi sel TROPOMI: desain DiD")
fig.tight_layout(); fig.savefig("data/processed/map_cell_classification.png", dpi=150)
print("peta: data/processed/map_cell_classification.png")