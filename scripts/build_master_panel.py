import pandas as pd
import numpy as np
from pathlib import Path

RAW, PROC = Path("data/raw"), Path("data/processed")

# ---------- 1. Panel ISPU utama ----------
p = pd.read_csv(PROC / "ispu_station_panel_2019_2025_FINAL.csv", parse_dates=["date"])
p = p[p.station_id.notna()].copy()

# ---------- 2. Cuaca: per jam -> harian per stasiun ----------
wmap = {"DKI1_BundaranHI":"DKI1","DKI2_KelapaGading":"DKI2","DKI3_Jagakarsa":"DKI3",
        "DKI4_LubangBuaya":"DKI4","DKI5_KebonJeruk":"DKI5"}
wx = []
for fname, sid in wmap.items():
    w = pd.read_csv(RAW / "weather" / f"{fname}.csv", parse_dates=["time"])
    w["date"] = w.time.dt.normalize()
    # arah angin: rata-rata vektor (rata-rata biasa salah utk data sirkular)
    rad = np.deg2rad(w.wind_direction_10m)
    w["wd_sin"], w["wd_cos"] = np.sin(rad), np.cos(rad)
    d = w.groupby("date").agg(
        temp=("temperature_2m","mean"), rh=("relative_humidity_2m","mean"),
        rain_mm=("precipitation","sum"), wind=("wind_speed_10m","mean"),
        wd_sin=("wd_sin","mean"), wd_cos=("wd_cos","mean")).reset_index()
    d["wind_dir"] = (np.rad2deg(np.arctan2(d.wd_sin, d.wd_cos)) + 360) % 360
    d["station_id"] = sid
    wx.append(d.drop(columns=["wd_sin","wd_cos"]))
wx = pd.concat(wx)

# ---------- 3. Kalender & regime gage ----------
hol = pd.read_csv(RAW / "calendar" / "holidays_id.csv", parse_dates=["date"])
hol["is_holiday"] = True
gg = pd.read_csv(RAW / "calendar" / "gage_daily_base.csv", parse_dates=["date"])

# ---------- 4. Gabung ----------
m = (p.merge(wx, on=["date","station_id"], how="left")
      .merge(hol[["date","is_holiday"]], on="date", how="left")
      .merge(gg[["date","regime","ruas","gage_on_base"]], on="date", how="left"))
m["is_holiday"] = m.is_holiday.fillna(False)
m["is_weekend"] = m.date.dt.dayofweek >= 5
m["gage_on"] = m.gage_on_base & ~m.is_holiday          # regime aktif & hari kerja & bukan libur
m["dow"] = m.date.dt.dayofweek
m["month"] = m.date.dt.month
m["t"] = (m.date - m.date.min()).dt.days               # tren waktu utk ITS
m["post"] = (m.date >= "2022-06-06").astype(int)       # dummy intervensi utama

m.to_csv(PROC / "master_panel_daily.csv", index=False)
print(f"master panel: {m.shape}, gage_on hari aktif: {m.gage_on.sum()} baris")
print("missing cuaca:", m.temp.isna().sum(), "| missing regime:", m.regime.isna().sum())

# ---------- 5. Plot EDA pertama ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

city = m.groupby("date").no2.mean().rolling(7, min_periods=3).mean()
fig, ax = plt.subplots(figsize=(15, 5.5))
colors = {"ON":"#2e7d32","ON_PARTIAL":"#f9a825","OFF":"#c62828","PRE":"#9e9e9e"}
for _, r in pd.read_csv(RAW/"calendar"/"gage_schedule.csv",
                        parse_dates=["start_date","end_date"]).iterrows():
    ax.axvspan(r.start_date, r.end_date, color=colors[r.status], alpha=0.12)
ax.plot(city.index, city.values, lw=1.1, color="#1a237e")
ax.axvline(pd.Timestamp("2022-06-06"), color="black", lw=1.8, ls="--")
ax.annotate("Reaktivasi penuh\n6 Jun 2022", xy=(pd.Timestamp("2022-06-06"), ax.get_ylim()[1]*0.95),
            fontsize=9, ha="left")
ax.set_ylabel("NO2 (ISPU, rata-rata 5 stasiun, MA-7)")
ax.set_title("NO2 Jakarta 2019–2025 — latar: regime ganjil-genap "
             "(hijau=ON, kuning=parsial, merah=OFF)")
fig.tight_layout()
fig.savefig(PROC / "eda_no2_timeline.png", dpi=150)
print("plot tersimpan: data/processed/eda_no2_timeline.png")

# ---------- 6. Plot verifikasi: per stasiun, sekitar dugaan patahan ----------
sub = m[(m.date >= "2020-06-01") & (m.date <= "2021-09-30")]
piv = sub.pivot_table(index="date", columns="station_id", values="no2").rolling(7, min_periods=3).mean()
axes = piv.plot(subplots=True, figsize=(14, 10), lw=1, color="#1a237e",
                title=[f"NO2 {s}" for s in piv.columns])
for ax in axes:
    ax.legend(loc="upper left", fontsize=8)
fig2 = axes[0].get_figure()
fig2.suptitle("Verifikasi patahan Okt-Nov 2020 per stasiun (MA-7)", y=1.00)
fig2.tight_layout()
fig2.savefig(PROC / "eda_break_check_per_station.png", dpi=150)
print("plot verifikasi tersimpan: data/processed/eda_break_check_per_station.png")

# ---------- 7. Flag episode anomali Okt-Nov 2020 ----------
anom = (m.date >= "2020-10-01") & (m.date <= "2020-12-15")
m.loc[anom, "dq_flag"] = m.loc[anom, "dq_flag"].fillna("") .astype(str).str.cat(
    ["anomaly_ispu_transition_2020"]*anom.sum(), sep="|").str.strip("|")
m.to_csv(PROC / "master_panel_daily.csv", index=False)
print("flag anomali:", anom.sum(), "baris")

# ---------- 8. Wasit TROPOMI: apakah kenaikan 2019->2021 asli? ----------
import glob
tro = pd.concat([pd.read_csv(f, parse_dates=["date"])
                 for f in glob.glob("data/raw/tropomi/tropomi_no2_jakarta_*.csv")])
tro["umol"] = tro["mean"] * 1e6
annual = tro.groupby(tro.date.dt.year).umol.mean()
monthly = tro.groupby(tro.date.dt.to_period("M")).umol.mean()
print("\nTROPOMI NO2 rata-rata tahunan (umol/m2):")
print(annual.round(1).to_string())

monthly.index = monthly.index.to_timestamp()
fig3, ax = plt.subplots(figsize=(13, 4))
monthly.plot(ax=ax, lw=1.2, color="#b71c1c",
             title="TROPOMI NO2 Jakarta bulanan (metodologi konsisten)")
ax.axvline(pd.Timestamp("2022-06-06"), color="black", ls="--")
fig3.tight_layout()
fig3.savefig(PROC / "eda_tropomi_monthly.png", dpi=150)