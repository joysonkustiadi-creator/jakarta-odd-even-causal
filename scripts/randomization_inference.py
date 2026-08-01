# =====================================================================
# M6 — RANDOMIZATION INFERENCE (penentu verdict akhir)
#
# Gagasan: alih-alih percaya pada satu p-value dari asumsi distribusi,
# kita bangun distribusi "efek palsu" dengan mengacak hal yang seharusnya
# tidak berpengaruh, lalu melihat di persentil berapa efek asli berada.
#
#   RI-A (ITS)  : intervensi fiktif di ~40 tanggal berbeda.
#   RI-B (DiD)  : label treated dipermutasi antar sel — dua versi:
#                 (i) acak murni, (ii) acak tapi tetap terkluster spasial
#                     (meniru kenyataan bahwa koridor gage bersebelahan).
#
# Output: 2 PNG histogram + tabel ringkas + CSV.
# Runtime: ~5-20 menit (tergantung N_PERM & mesin). Turunkan N_PERM bila lama.
# =====================================================================
import pandas as pd, numpy as np, glob, time
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
import pyfixest as pf

PROC = "data/processed/"
INTV = pd.Timestamp("2022-06-06")
N_PERM = 200          # permutasi DiD (turunkan ke 100 bila terlalu lama)
SEED = 42
rng = np.random.default_rng(SEED)
ringkas = []

# =====================================================================
# RI-A : ITS dengan tanggal intervensi fiktif
# =====================================================================
print("=" * 70); print("RI-A : ITS placebo dates"); print("=" * 70)

mp = pd.read_csv(PROC + "master_panel_daily.csv", parse_dates=["date"])
mp = mp[(mp.date >= "2021-01-01") & mp.station_id.notna()]
mp = mp[~mp.dq_flag.astype(str).str.contains("anomaly", na=False)]

hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])
eids = hol[hol.holiday_name.str.contains("Eid al-Fitr", case=False)].date
ram = {e + pd.Timedelta(days=k) for e in eids for k in range(-30, 8)}

city = (mp.groupby("date")
          .agg(no2=("no2", "mean"), temp=("temp", "mean"), rain=("rain_mm", "mean"),
               wind=("wind", "mean"), rh=("rh", "mean"),
               is_holiday=("is_holiday", "max"))
          .reset_index().dropna(subset=["no2"]))
city["ramadan"] = city.date.isin(ram).astype(int)

def its_level_shift(df, intv):
    """Kembalikan koefisien level shift (post) untuk tanggal intervensi tertentu."""
    c = df.copy()
    c["t"] = (c.date - c.date.min()).dt.days
    c["post"] = (c.date >= intv).astype(int)
    if c.post.nunique() < 2 or c.post.sum() < 60 or (1 - c.post).sum() < 60:
        return np.nan
    c["t_post"] = c.t * c.post - c.t[c.post == 1].min() * c.post
    doy = c.date.dt.dayofyear
    for k in (1, 2):
        c[f"sin{k}"] = np.sin(2 * np.pi * k * doy / 365.25)
        c[f"cos{k}"] = np.cos(2 * np.pi * k * doy / 365.25)
    dow = pd.get_dummies(c.date.dt.dayofweek, prefix="dow",
                         drop_first=True).astype(float)
    X = pd.concat([c[["t", "post", "t_post", "sin1", "cos1", "sin2", "cos2",
                      "ramadan", "temp", "rain", "wind", "rh"]],
                   c.is_holiday.astype(float).rename("holiday"), dow], axis=1)
    X = sm.add_constant(X); ok = X.notna().all(axis=1)
    try:
        r = sm.OLS(c.no2[ok], X[ok]).fit(cov_type="HAC", cov_kwds={"maxlags": 14})
        return r.params["post"]
    except Exception:
        return np.nan

true_its = its_level_shift(city, INTV)
print(f"efek asli (6 Jun 2022): {true_its:+.3f}")

# kandidat tanggal fiktif: tanggal 6 tiap bulan, kecuali +-6 bulan dari intervensi asli
cands = pd.date_range("2021-04-06", "2025-06-06", freq="MS") + pd.Timedelta(days=5)
cands = [d for d in cands if abs((d - INTV).days) > 183]
fake = []
for d in cands:
    v = its_level_shift(city, d)
    if not np.isnan(v):
        fake.append({"date": d, "coef": v})
fake = pd.DataFrame(fake)
p_its = (np.abs(fake.coef) >= abs(true_its)).mean()
pct = (fake.coef <= true_its).mean() * 100
print(f"n tanggal fiktif: {len(fake)}")
print(f"RI p-value (dua sisi): {p_its:.3f}")
print(f"efek asli berada di persentil {pct:.0f} dari distribusi palsu")
ringkas.append({"uji": "RI-A ITS placebo dates", "efek_asli": round(true_its, 3),
                "n_perm": len(fake), "ri_p": round(p_its, 4),
                "persentil": round(pct, 1)})

fig, ax = plt.subplots(figsize=(9, 4))
ax.hist(fake.coef, bins=18, color="#90a4ae", edgecolor="white")
ax.axvline(true_its, color="#c62828", lw=2.4, label=f"efek asli {true_its:+.2f}")
ax.axvline(0, color="grey", lw=0.8, ls=":")
ax.set_xlabel("level shift (poin ISPU) pada tanggal intervensi fiktif")
ax.set_ylabel("frekuensi"); ax.legend()
ax.set_title(f"RI-A: distribusi efek palsu ITS (n={len(fake)}), RI p={p_its:.3f}")
fig.tight_layout(); fig.savefig(PROC + "m6_ri_its.png", dpi=150)
print("plot: m6_ri_its.png")

# =====================================================================
# RI-B : DiD dengan label treated dipermutasi
# =====================================================================
print("\n" + "=" * 70); print("RI-B : DiD permutasi label treated"); print("=" * 70)

tro = pd.concat([pd.read_csv(f, parse_dates=["date"])
                 for f in glob.glob("data/raw/tropomi/*.csv")])
tro["umol"] = tro["mean"] * 1e6
cl = pd.read_csv(PROC + "tropomi_cells_classified.csv")
gg = pd.read_csv("data/raw/calendar/gage_daily_base.csv", parse_dates=["date"])

D = (tro.merge(cl[["cell_id", "group", "dist_km", "lon", "lat"]], on="cell_id")
        .merge(gg[["date", "regime"]], on="date"))
D["is_holiday"] = D.date.isin(set(hol.date))
D = D[D.group.isin(["treated_13ruas", "treated_both", "treated_new12",
                    "control"])].dropna(subset=["umol"])
D = D[(D.umol > 0) & (D.dist_km <= 15)].copy()      # spesifikasi utama (D10)
D["lumol"] = np.log(D.umol)
D["workday"] = ((D.date.dt.dayofweek < 5) & ~D.is_holiday).astype(int)
D["regime_on"] = D.regime.isin(["ON", "ON_PARTIAL"]).astype(int)

cells = cl[cl.cell_id.isin(D.cell_id.unique())][["cell_id", "lon", "lat", "group"]].copy()
true_treated = set(cells.loc[cells.group.str.startswith("treated"), "cell_id"])
K = len(true_treated)
print(f"sel dalam sampel: {len(cells)} | treated asli: {K}")

SPEC = ("lumol ~ treated:workday + treated:regime_on + treated:workday:regime_on"
        " | cell_id + date")
KEY = "treated:workday:regime_on"

def fit_coef(treated_ids):
    d = D.copy()
    d["treated"] = d.cell_id.isin(treated_ids).astype(int)
    if d.treated.nunique() < 2:
        return np.nan
    try:
        m = pf.feols(SPEC, data=d, vcov={"CRV1": "cell_id"})
        t = m.tidy().reset_index()
        return float(t.loc[t["Coefficient"] == KEY, "Estimate"].iloc[0])
    except Exception:
        return np.nan

true_did = fit_coef(true_treated)
print(f"efek asli (log): {true_did:+.4f}  (= {true_did*100:+.2f}%)")

coords = cells[["lon", "lat"]].to_numpy()
ids = cells.cell_id.to_numpy()

def perm_random():
    return set(rng.choice(ids, size=K, replace=False))

def perm_spatial():
    """Pilih 1 sel acak sebagai pusat, ambil K sel terdekat -> meniru kluster koridor."""
    c = rng.integers(len(ids))
    d2 = ((coords - coords[c]) ** 2).sum(axis=1)
    return set(ids[np.argsort(d2)[:K]])

t0 = time.time()
res_b = []
for i in range(N_PERM):
    kind = "spatial" if i % 2 == 0 else "random"
    ids_p = perm_spatial() if kind == "spatial" else perm_random()
    if ids_p == true_treated:
        continue
    v = fit_coef(ids_p)
    if not np.isnan(v):
        res_b.append({"kind": kind, "coef": v})
    if (i + 1) % 20 == 0:
        print(f"  {i+1}/{N_PERM} permutasi ({time.time()-t0:.0f}s)")
res_b = pd.DataFrame(res_b)

for kind in ["spatial", "random"]:
    s = res_b[res_b.kind == kind].coef
    if len(s) == 0:
        continue
    p = (np.abs(s) >= abs(true_did)).mean()
    pct = (s <= true_did).mean() * 100
    print(f"\nRI-B [{kind}] n={len(s)} | RI p={p:.3f} | persentil {pct:.0f}")
    ringkas.append({"uji": f"RI-B DiD permutasi ({kind})",
                    "efek_asli": round(true_did, 4), "n_perm": len(s),
                    "ri_p": round(p, 4), "persentil": round(pct, 1)})

fig, ax = plt.subplots(figsize=(9, 4))
for kind, c in [("spatial", "#7e57c2"), ("random", "#26a69a")]:
    s = res_b[res_b.kind == kind].coef
    if len(s):
        ax.hist(s, bins=16, alpha=0.55, color=c, label=f"{kind} (n={len(s)})")
ax.axvline(true_did, color="#c62828", lw=2.4, label=f"efek asli {true_did:+.3f}")
ax.axvline(0, color="grey", lw=0.8, ls=":")
ax.set_xlabel("koefisien triple-diff (log NO2) pada label treated palsu")
ax.set_ylabel("frekuensi"); ax.legend(fontsize=8)
ax.set_title("RI-B: distribusi efek palsu DiD (permutasi label sel)")
fig.tight_layout(); fig.savefig(PROC + "m6_ri_did.png", dpi=150)
print("plot: m6_ri_did.png")

# =====================================================================
R = pd.DataFrame(ringkas)
print("\n" + "=" * 70); print("RANGKUMAN RANDOMIZATION INFERENCE"); print("=" * 70)
print(R.to_string(index=False))
R.to_csv(PROC + "m6_randomization_inference.csv", index=False)
print("\ntersimpan: m6_randomization_inference.csv")
print("""
CARA BACA (tetapkan sebelum melihat angka):
  RI p < 0,05  -> efek asli ekstrem dibanding efek palsu = bukti kuat.
  RI p 0,05-0,15 -> sugestif; laporkan sebagai indikasi, bukan bukti.
  RI p > 0,15  -> desain tidak informatif; laporkan nol/tak konklusif dengan jujur.
Persentil <5 atau >95 = efek asli di ekor distribusi (arah negatif = persentil kecil).
""")