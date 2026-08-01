# =====================================================================
# M5 — PAKET UJI KETAHANAN
# R1 log+cincin | R2 mingguan | R3 placebo outcome | R4 placebo tanggal
# R5 tren pra-intervensi | R6 tanpa baris ber-flag | R7 sensitivitas jendela
# Semua hasil dirangkum di tabel akhir + disimpan ke CSV.
# =====================================================================
import pandas as pd, numpy as np, glob
import statsmodels.api as sm
import pyfixest as pf

PROC = "data/processed/"
INTV = pd.Timestamp("2022-06-06")
hasil = []   # (uji, koef, se, p, catatan)

def add(uji, est, se, p, note=""):
    hasil.append({"uji": uji, "koef": round(est, 3), "se": round(se, 3),
                  "p": round(p, 4), "catatan": note})

def pull(m, term):
    t = m.tidy().reset_index()
    r = t[t["Coefficient"] == term].iloc[0]
    return r["Estimate"], r["Std. Error"], r["Pr(>|t|)"]

# ---------- panel TROPOMI (dipakai R1,R2,R5,R7) ----------
tro = pd.concat([pd.read_csv(f, parse_dates=["date"])
                 for f in glob.glob("data/raw/tropomi/*.csv")])
tro["umol"] = tro["mean"] * 1e6
cl = pd.read_csv(PROC + "tropomi_cells_classified.csv")
gg = pd.read_csv("data/raw/calendar/gage_daily_base.csv", parse_dates=["date"])
hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])
D = (tro.merge(cl[["cell_id", "group", "dist_km"]], on="cell_id")
        .merge(gg[["date", "regime"]], on="date"))
D["is_holiday"] = D.date.isin(set(hol.date))
D = D[D.group.isin(["treated_13ruas", "treated_both", "treated_new12",
                    "control"])].dropna(subset=["umol"])
D["treated"] = D.group.str.startswith("treated").astype(int)
D["workday"] = ((D.date.dt.dayofweek < 5) & ~D.is_holiday).astype(int)
D["regime_on"] = D.regime.isin(["ON", "ON_PARTIAL"]).astype(int)
SPEC = "~ treated:workday + treated:regime_on + treated:workday:regime_on | cell_id + date"
KEY = "treated:workday:regime_on"

# baseline M1 (pembanding)
m0 = pf.feols("umol " + SPEC, data=D, vcov={"CRV1": "cell_id"})
add("M1 baseline (level, semua kontrol)", *pull(m0, KEY))

# ---------- R1: log outcome + kontrol cincin <=15 km ----------
R1 = D[(D.umol > 0) & (D.dist_km <= 15)].copy()
R1["lumol"] = np.log(R1.umol)
m1 = pf.feols("lumol " + SPEC, data=R1, vcov={"CRV1": "cell_id"})
e, s, p = pull(m1, KEY)
add("R1 log + cincin<=15km", e, s, p, f"={e*100:.1f}% efek proporsional")

# ---------- R2: agregasi mingguan ----------
D["week"] = D.date.dt.to_period("W").astype(str)
W = (D.groupby(["cell_id", "week", "treated"])
       .agg(umol=("umol", "mean"), regime_on=("regime_on", "mean"))
       .reset_index())
W["regime_on"] = (W.regime_on > 0.5).astype(int)
m2 = pf.feols("umol ~ treated:regime_on | cell_id + week",
              data=W, vcov={"CRV1": "cell_id"})
add("R2 mingguan: treated:regime_on", *pull(m2, "treated:regime_on"),
    "kontras rezim saja (workday hilang di mingguan)")

# ---------- R5: tren pra-intervensi (paralel?) ----------
P = D[(D.date >= "2021-01-01") & (D.date < INTV)].copy()
P["t"] = (P.date - P.date.min()).dt.days / 30.0
m5 = pf.feols("umol ~ treated:t | cell_id + date", data=P,
              vcov={"CRV1": "cell_id"})
add("R5 pre-trend treated:t (per 30 hari; harus ~0)", *pull(m5, "treated:t"))

# ---------- R7: sensitivitas jendela ----------
for lab, sub in [("R7a 2019-2023", D[D.date < "2024-01-01"]),
                 ("R7b 2021-2026", D[D.date >= "2021-01-01"])]:
    mm = pf.feols("umol " + SPEC, data=sub, vcov={"CRV1": "cell_id"})
    add(lab, *pull(mm, KEY))

# ---------- ITS untuk R3, R4, R6 ----------
def run_its(city, intv, outcome="no2"):
    c = city.dropna(subset=[outcome]).copy()
    c["t"] = (c.date - c.date.min()).dt.days
    c["post"] = (c.date >= intv).astype(int)
    c["t_post"] = c.t * c.post - (c.t[c.post == 1].min() if c.post.any() else 0) * c.post
    doy = c.date.dt.dayofyear
    for k in (1, 2):
        c[f"sin{k}"] = np.sin(2*np.pi*k*doy/365.25)
        c[f"cos{k}"] = np.cos(2*np.pi*k*doy/365.25)
    dow = pd.get_dummies(c.date.dt.dayofweek, prefix="dow",
                         drop_first=True).astype(float)
    X = pd.concat([c[["t", "post", "t_post", "sin1", "cos1", "sin2", "cos2",
                      "ramadan", "temp", "rain", "wind", "rh"]],
                   c.is_holiday.astype(float).rename("holiday"), dow], axis=1)
    X = sm.add_constant(X); ok = X.notna().all(axis=1)
    r = sm.OLS(c[outcome][ok], X[ok]).fit(cov_type="HAC",
                                          cov_kwds={"maxlags": 14})
    return (r.params["post"], r.bse["post"], r.pvalues["post"])

mp = pd.read_csv(PROC + "master_panel_daily.csv", parse_dates=["date"])
mp = mp[(mp.date >= "2021-01-01") & mp.station_id.notna()]
mp = mp[~mp.dq_flag.astype(str).str.contains("anomaly", na=False)]
eids = hol[hol.holiday_name.str.contains("Eid al-Fitr", case=False)].date
ram = {e + pd.Timedelta(days=k) for e in eids for k in range(-30, 8)}
def make_city(df):
    c = (df.groupby("date").agg(no2=("no2","mean"), o3=("o3","mean"),
         so2=("so2","mean"), temp=("temp","mean"), rain=("rain_mm","mean"),
         wind=("wind","mean"), rh=("rh","mean"),
         is_holiday=("is_holiday","max")).reset_index())
    c["ramadan"] = c.date.isin(ram).astype(int)
    return c
city = make_city(mp)

add("ITS baseline: level shift NO2", *run_its(city, INTV, "no2"))
# R3 placebo outcomes
add("R3a placebo O3 (harus ~0)", *run_its(city, INTV, "o3"))
add("R3b placebo SO2 (harus ~0)", *run_its(city, INTV, "so2"))
# R4 placebo tanggal: fake 2021-09-01, sampel berakhir sebelum intervensi asli
fake = city[city.date < INTV]
add("R4 placebo tanggal 2021-09-01 (harus ~0)",
    *run_its(fake, pd.Timestamp("2021-09-01"), "no2"))
# R6 tanpa baris ber-flag (tanpa tambalan scraping dll.)
clean = mp[mp.dq_flag.isna() | (mp.dq_flag.astype(str) == "") |
           (mp.dq_flag.astype(str) == "nan")]
add("R6 ITS tanpa baris ber-flag", *run_its(make_city(clean), INTV, "no2"),
    f"n hari={clean.date.nunique()}")

# ---------- rangkuman ----------
R = pd.DataFrame(hasil)
R["sig"] = np.where(R.p < 0.05, "*", np.where(R.p < 0.1, ".", ""))
print("\n" + "="*72)
print("RANGKUMAN UJI KETAHANAN")
print("="*72)
print(R.to_string(index=False))
R.to_csv(PROC + "m5_robustness_summary.csv", index=False)
print("\ntersimpan: m5_robustness_summary.csv")
print("\nCara baca: baris 'harus ~0' yang ternyata signifikan = lampu merah "
      "identifikasi; baris efek utama yang stabil lintas spesifikasi = "
      "temuan yang layak diklaim.")
