import pandas as pd, numpy as np, glob

# ---- panel: TROPOMI semua tahun + klasifikasi + regime gage ----
tro = pd.concat([pd.read_csv(f, parse_dates=["date"])
                 for f in glob.glob("data/raw/tropomi/*.csv")])
tro["umol"] = tro["mean"] * 1e6
cl = pd.read_csv("data/processed/tropomi_cells_classified.csv")
gg = pd.read_csv("data/raw/calendar/gage_daily_base.csv", parse_dates=["date"])
hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])

df = (tro.merge(cl[["cell_id", "group"]], on="cell_id")
         .merge(gg[["date", "regime", "gage_on_base"]], on="date"))
df["is_holiday"] = df.date.isin(set(hol.date))
df = df[df.group.isin(["treated_13ruas", "treated_both", "treated_new12", "control"])]
df["treated"] = df.group.str.startswith("treated").astype(int)
df = df.dropna(subset=["umol"])
print(f"observasi: {len(df):,} | treated: {df.treated.mean()*100:.0f}% baris")

# ---- Triple difference ----
import pyfixest as pf

df["workday"] = ((df.date.dt.dayofweek < 5) & ~df.is_holiday).astype(int)
df["regime_on"] = df.regime.isin(["ON", "ON_PARTIAL"]).astype(int)

m3 = pf.feols(
    "umol ~ treated:workday + treated:regime_on + treated:workday:regime_on"
    " | cell_id + date",
    data=df, vcov={"CRV1": "cell_id"})
print("\n=== TRIPLE DIFFERENCE (2019-2026) ===")
print(m3.summary())

# ---- Robustness: era pasca-COVID saja (2022+), on/off dari jeda libur ----
post = df[df.date >= "2022-06-06"]
m4 = pf.feols(
    "umol ~ treated:workday | cell_id + date",
    data=post, vcov={"CRV1": "cell_id"})
print("\n=== PEMBANDING ERA ON PENUH SAJA (2022+): workday-differential ===")
print(m4.summary())
# ---- Simpan koefisien ke CSV (untuk dashboard & pelaporan) ----
import pandas as pd

def tidy(model, label):
    t = model.tidy().reset_index()
    t.insert(0, "model", label)
    return t

pd.concat([tidy(m3, "M1_triple_diff_2019_2026"),
           tidy(m4, "M1b_era_ON_2022plus")]) \
  .to_csv("data/processed/m1_coefficients.csv", index=False)
print("\nkoefisien tersimpan: data/processed/m1_coefficients.csv")