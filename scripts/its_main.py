# =====================================================================
# M3 — ITS ERA-KONSISTEN (2021+) + ESTIMASI NAIF PEMBANDING
# Deret NO2 stasiun (rata-rata kota) dgn level shift & slope change di
# 6 Jun 2022, kontrol musiman-harmonik, hari, libur, Ramadan, cuaca.
# SE Newey-West. Plus: naif sebelum-vs-sesudah yang sengaja "dibantah".
# =====================================================================
import pandas as pd, numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm

PROC = "data/processed/"
INTV = pd.Timestamp("2022-06-06")

# ---------- 1. Data: era metodologi konsisten ----------
m = pd.read_csv(PROC + "master_panel_daily.csv", parse_dates=["date"])
m = m[(m.date >= "2021-01-01") & m.station_id.notna()]
m = m[~m.dq_flag.astype(str).str.contains("anomaly", na=False)]

city = (m.groupby("date")
          .agg(no2=("no2", "mean"), o3=("o3", "mean"), so2=("so2", "mean"),
               temp=("temp", "mean"), rain=("rain_mm", "mean"),
               wind=("wind", "mean"), rh=("rh", "mean"),
               is_holiday=("is_holiday", "max"))
          .reset_index().dropna(subset=["no2"]))

# Ramadan+mudik: 30 hari sebelum s.d. 7 hari sesudah Idul Fitri
hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])
eids = hol[hol.holiday_name.str.contains("Eid al-Fitr", case=False)].date
ram = set()
for e in eids:
    for k in range(-30, 8):
        ram.add(e + pd.Timedelta(days=k))
city["ramadan"] = city.date.isin(ram).astype(int)

# ---------- 2. Naif: sebelum vs sesudah ----------
pre, post = city[city.date < INTV], city[city.date >= INTV]
print("=== ESTIMASI NAIF (untuk dibantah) ===")
print(f"rata2 NO2 pra ({pre.date.min().date()}..): {pre.no2.mean():.2f}")
print(f"rata2 NO2 pasca (..{post.date.max().date()}): {post.no2.mean():.2f}")
print(f"selisih naif: {post.no2.mean()-pre.no2.mean():+.2f} poin "
      f"({(post.no2.mean()/pre.no2.mean()-1)*100:+.1f}%)")
w6 = city[(city.date >= INTV - pd.Timedelta(days=183)) &
          (city.date < INTV + pd.Timedelta(days=183))]
print(f"naif jendela +-6 bulan: "
      f"{w6[w6.date>=INTV].no2.mean()-w6[w6.date<INTV].no2.mean():+.2f} poin")

# ---------- 3. Model ITS ----------
c = city.copy()
c["t"] = (c.date - c.date.min()).dt.days
c["post"] = (c.date >= INTV).astype(int)
c["t_post"] = c.t * c.post - c.t[c.post == 1].min() * c.post  # slope sejak intervensi
doy = c.date.dt.dayofyear
for k in (1, 2):
    c[f"sin{k}"] = np.sin(2 * np.pi * k * doy / 365.25)
    c[f"cos{k}"] = np.cos(2 * np.pi * k * doy / 365.25)
dow = pd.get_dummies(c.date.dt.dayofweek, prefix="dow", drop_first=True).astype(float)
X = pd.concat([c[["t", "post", "t_post", "sin1", "cos1", "sin2", "cos2",
                  "ramadan", "temp", "rain", "wind", "rh"]],
               c.is_holiday.astype(float).rename("holiday"), dow], axis=1)
X = sm.add_constant(X)
ok = X.notna().all(axis=1)
res = sm.OLS(c.no2[ok], X[ok]).fit(cov_type="HAC", cov_kwds={"maxlags": 14})
print("\n=== M3 ITS (2021+, Newey-West lag 14) ===")
print(res.summary().tables[1])
print(f"\nlevel shift (post): {res.params['post']:+.2f} "
      f"[{res.conf_int().loc['post',0]:.2f}, {res.conf_int().loc['post',1]:.2f}]")
print(f"slope change (t_post, per 30 hari): {res.params['t_post']*30:+.3f}")

# ---- Simpan koefisien + estimasi naif ke CSV ----
ci = res.conf_int()
pd.DataFrame({"coef": res.params, "se": res.bse, "t": res.tvalues,
              "p": res.pvalues, "ci_low": ci[0], "ci_high": ci[1]}) \
  .rename_axis("term").to_csv(PROC + "m3_its_coefficients.csv")
pd.DataFrame([
    {"ukuran": "naif_selisih_rata2", "nilai": post.no2.mean() - pre.no2.mean()},
    {"ukuran": "naif_persen", "nilai": (post.no2.mean()/pre.no2.mean()-1)*100},
    {"ukuran": "naif_jendela_6bulan",
     "nilai": w6[w6.date>=INTV].no2.mean() - w6[w6.date<INTV].no2.mean()},
    {"ukuran": "its_level_shift", "nilai": res.params["post"]},
    {"ukuran": "its_slope_per_30hari", "nilai": res.params["t_post"]*30},
]).to_csv(PROC + "m3_its_summary.csv", index=False)
print("koefisien tersimpan: m3_its_coefficients.csv, m3_its_summary.csv")

# ---------- 4. Counterfactual plot ----------
Xc = X[ok].copy(); Xc["post"] = 0; Xc["t_post"] = 0
c.loc[ok, "fit"] = res.predict(X[ok])
c.loc[ok, "cf"] = res.predict(Xc)
fig, ax = plt.subplots(figsize=(14, 4.5))
ax.plot(c.date, c.no2.rolling(7, min_periods=3).mean(), lw=0.9,
        color="#9e9e9e", label="aktual (MA-7)")
ax.plot(c.date[ok], c.fit[ok].rolling(7, min_periods=3).mean(), lw=1.4,
        color="#1a237e", label="model")
ax.plot(c.date[ok & (c.post == 1)],
        c.cf[ok & (c.post == 1)].rolling(7, min_periods=3).mean(),
        lw=1.6, ls="--", color="#c62828", label="counterfactual (tanpa gage-25)")
ax.axvline(INTV, color="black", ls=":", lw=1.5)
ax.set_ylabel("NO2 (ISPU, rata2 kota)"); ax.legend()
ax.set_title("ITS 2021+ : aktual vs counterfactual")
fig.tight_layout(); fig.savefig(PROC + "m3_its_counterfactual.png", dpi=150)
print("\nplot: m3_its_counterfactual.png")
print("\nBaca hasil dgn disiplin: 'post' di sini menangkap SEMUA yang berubah "
      "sejak Jun 2022 (termasuk pemulihan lalu lintas yang tak tertangkap "
      "tren+musiman) — bandingkan arahnya dgn M1/M2 (desain spasial/jam), "
      "bukan diperlakukan sebagai bukti tunggal.")