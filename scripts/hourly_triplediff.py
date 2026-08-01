# =====================================================================
# M2 — TRIPLE-DIFF PER JAM (2022)
# Sidik jari kebijakan: penurunan NO2 harus muncul TEPAT di jam gage
# (06-10 & 16-21) pada hari kerja, di stasiun dekat koridor — dan tidak
# di jam lain / akhir pekan / stasiun jauh.
# Output: data/processed/m2_*.png + hasil regresi di terminal.
# =====================================================================
import pandas as pd, numpy as np, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point
import pyfixest as pf

PROC = "data/processed/"

# ---------- 1. Data per jam ----------
h = pd.read_csv(PROC + "ispu_hourly_2022_clean.csv", parse_dates=["tanggal"])
h["hour"] = h.jam.astype(str).str.extract(r"^(\d{1,2})")[0].astype(int)
h = h.rename(columns={"tanggal": "date"})

hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])
h["is_holiday"] = h.date.isin(set(hol.date))
h["workday"] = ((h.date.dt.dayofweek < 5) & ~h.is_holiday).astype(int)

# ---------- 2. Klasifikasi stasiun dekat/jauh koridor gage ----------
st = pd.read_csv("data/raw/geo/stations.csv")
gj = json.load(open("data/raw/geo/gage_roads_v0_approx.geojson"))
roads = [LineString(f["geometry"]["coordinates"]) for f in gj["features"]]
st["dist_km"] = st.apply(lambda r: min(Point(r.lon, r.lat).distance(g)
                                       for g in roads) * 111.32, axis=1)
NEAR_KM = 1.5
st["near"] = (st.dist_km < NEAR_KM).astype(int)
print("Jarak stasiun ke ruas gage terdekat (km):")
print(st[["station_id", "dist_km", "near"]].round(2).to_string(index=False))
h = h.merge(st[["station_id", "near"]], on="station_id")

# ---------- 3. Deskriptif: profil NO2 per jam (sidik jari visual) ----------
prof = (h.groupby(["station_id", "workday", "hour"]).no2.mean().reset_index())
fig, axes = plt.subplots(1, 5, figsize=(18, 3.6), sharey=True)
for ax, sid in zip(axes, ["DKI1", "DKI2", "DKI3", "DKI4", "DKI5"]):
    for wd, lab, c in [(1, "hari kerja", "#c62828"), (0, "akhir pekan/libur", "#1565c0")]:
        s = prof[(prof.station_id == sid) & (prof.workday == wd)]
        ax.plot(s.hour, s.no2, label=lab, color=c, lw=1.6)
    for a, b in [(6, 10), (16, 21)]:
        ax.axvspan(a, b, color="grey", alpha=0.15)
    ax.set_title(f"{sid}{' (dekat gage)' if st.set_index('station_id').near[sid] else ''}",
                 fontsize=10)
    ax.set_xlabel("jam")
axes[0].set_ylabel("NO2 (ISPU per jam)"); axes[0].legend(fontsize=8)
fig.suptitle("Profil NO2 per jam 2022 — area abu = jam gage", y=1.02)
fig.tight_layout(); fig.savefig(PROC + "m2_hourly_profile.png", dpi=150,
                                bbox_inches="tight")
print("\nplot profil: m2_hourly_profile.png")

# ---------- 4. Differential harian: jam-gage vs jam-siang non-gage ----------
GAGE_H = list(range(6, 10)) + list(range(16, 21))   # 06-09, 16-20
MID_H = list(range(11, 16))                          # 11-15 pembanding
def daily_diff(g):
    a = g.loc[g.hour.isin(GAGE_H), "no2"].dropna()
    b = g.loc[g.hour.isin(MID_H), "no2"].dropna()
    if len(a) >= 3 and len(b) >= 2:
        return pd.Series({"gd": a.mean() - b.mean(),
                          "n_gage": len(a), "n_mid": len(b)})
    return pd.Series({"gd": np.nan, "n_gage": len(a), "n_mid": len(b)})

d = (h.groupby(["station_id", "date", "workday", "near"])
       .apply(daily_diff, include_groups=False).reset_index())
d = d.dropna(subset=["gd"])
print(f"\nobservasi stasiun-hari dgn differential valid: {len(d):,}")

# ---------- 5. Estimasi inti ----------
# gd = (NO2 jam gage − NO2 jam siang) per stasiun-hari.
# FE stasiun menyerap perbedaan permanen; FE tanggal menyerap segala hal
# se-kota di hari itu (cuaca, musim, libur). Koefisien kunci:
# workday:near = pada hari kerja (gage aktif), differential jam-gage stasiun
# koridor berubah berapa relatif stasiun jauh. Negatif = gage menekan puncak.
d["date_s"] = d.date.dt.strftime("%Y-%m-%d")
m = pf.feols("gd ~ workday:near | station_id + date_s",
             data=d, vcov={"CRV1": "date_s"})
print("\n=== M2 UTAMA (2022 penuh) ===")
print(m.summary())

# pecah per periode: 13-ruas (s.d. 5 Jun) vs 25-ruas (6 Jun+)
hasil_m2 = [("M2_utama_2022", m)]
for lab, sub in [("M2_13ruas_jan_5jun", d[d.date < "2022-06-06"]),
                 ("M2_25ruas_6jun_des", d[d.date >= "2022-06-06"])]:
    ms = pf.feols("gd ~ workday:near | station_id + date_s",
                  data=sub, vcov={"CRV1": "date_s"})
    print(f"\n=== {lab} ===")
    print(ms.summary())
    hasil_m2.append((lab, ms))

# ---------- 6. Placebo jam: differential malam (22-02) — harus ~0 ----------
NIGHT_H = [22, 23, 0, 1, 2]
def night_diff(g):
    a = g.loc[g.hour.isin(NIGHT_H), "no2"].dropna()
    b = g.loc[g.hour.isin(MID_H), "no2"].dropna()
    return a.mean() - b.mean() if (len(a) >= 2 and len(b) >= 2) else np.nan
dn = (h.groupby(["station_id", "date", "workday", "near"])
        .apply(night_diff, include_groups=False).rename("gd").reset_index()
        .dropna(subset=["gd"]))
dn["date_s"] = dn.date.dt.strftime("%Y-%m-%d")
mp = pf.feols("gd ~ workday:near | station_id + date_s",
              data=dn, vcov={"CRV1": "date_s"})
print("\n=== M2 PLACEBO (jam malam 22-02; koef harus ~0) ===")
print(mp.summary())
hasil_m2.append(("M2_placebo_jam_malam", mp))

# ---- Simpan koefisien ke CSV ----
tab = []
for lab, mod in hasil_m2:
    t = mod.tidy().reset_index()
    t.insert(0, "model", lab)
    tab.append(t)
pd.concat(tab).to_csv(PROC + "m2_coefficients.csv", index=False)
print("\nkoefisien tersimpan: m2_coefficients.csv")
print("\nCATATAN: hanya 1 stasiun 'near' (DKI1) -> inferensi bertumpu pada "
      "kontras jam & hari, cluster SE per tanggal. Cek juga kepadatan jam "
      "malam (15%) membuat placebo ini kurang presisi — baca dengan hati-hati.")