# =====================================================================
# M4 — EVENT STUDY SAKELAR LIBUR (era pasca-COVID, TROPOMI)
# Saat gage dijeda pada minggu libur panjang (Lebaran, Natal-Tahun Baru,
# jeda resmi 2026), apakah lonjakan NO2 hari-kerja di koridor kembali?
# Eksperimen alami bebas kontaminasi COVID.
# =====================================================================
import pandas as pd, numpy as np, glob
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyfixest as pf

PROC = "data/processed/"

# ---------- 1. Panel TROPOMI + klasifikasi ----------
tro = pd.concat([pd.read_csv(f, parse_dates=["date"])
                 for f in glob.glob("data/raw/tropomi/*.csv")])
tro["umol"] = tro["mean"] * 1e6
cl = pd.read_csv(PROC + "tropomi_cells_classified.csv")
df = tro.merge(cl[["cell_id", "group"]], on="cell_id")
df = df[df.group.isin(["treated_13ruas", "treated_both", "treated_new12",
                       "control"])].dropna(subset=["umol"])
df["treated"] = df.group.str.startswith("treated").astype(int)

hol = pd.read_csv("data/raw/calendar/holidays_id.csv", parse_dates=["date"])
gg = pd.read_csv("data/raw/calendar/gage_daily_base.csv", parse_dates=["date"])
df = df.merge(gg[["date", "regime"]], on="date", how="left")
df["is_holiday"] = df.date.isin(set(hol.date))
df["workday"] = ((df.date.dt.dayofweek < 5) & ~df.is_holiday).astype(int)

# ---------- 2. Definisi jendela jeda (pause) ----------
# Lebaran: +-4 hari sekitar Idul Fitri; Natal-TahunBaru: 24 Des-2 Jan;
# plus jeda resmi 2026 (regime OFF di gage_schedule).
eids = hol[hol.holiday_name.str.contains("Eid al-Fitr", case=False)].date
pause = set()
for e in eids:
    for k in range(-4, 6):
        pause.add(e + pd.Timedelta(days=k))
for y in range(2022, 2027):
    for dt in pd.date_range(f"{y}-12-24", f"{y+1}-01-02"):
        pause.add(dt)
df["pause"] = (df.date.isin(pause) | (df.regime == "OFF")).astype(int)

# sampel: era ON penuh pasca-COVID
df = df[df.date >= "2022-06-06"].copy()
df["pause_workday"] = df.pause * df.workday
print(f"observasi: {len(df):,} | hari-kerja-jeda unik: "
      f"{df.loc[df.pause_workday==1, 'date'].nunique()}")

# ---------- 3. Estimasi ----------
# treated:workday          = lonjakan hari-kerja normal koridor (gage aktif)
# treated:pause_workday    = TAMBAHAN pada hari kerja yang gage-nya dijeda.
#   Jika gage menekan polusi: jeda -> lonjakan pulih -> koefisien POSITIF.
#   Peringatan interpretasi: hari jeda juga hari mudik (komuter turun),
#   yang menekan koefisien ke bawah -> estimasi ini adalah BATAS BAWAH.
m = pf.feols("umol ~ treated:workday + treated:pause_workday | cell_id + date",
             data=df, vcov={"CRV1": "cell_id"})
print("\n=== M4 EVENT STUDY SAKELAR (2022-06-06+) ===")
print(m.summary())

# ---------- 4. Plot event: profil harian sekitar Lebaran ----------
# treated-minus-control per hari, disejajarkan pada hari-H tiap Lebaran 2023+
tc = (df.groupby(["date", "treated"]).umol.mean().unstack()
        .rename(columns={0: "control", 1: "treated"}))
tc["gap"] = tc.treated - tc.control
rows = []
for e in eids[eids >= "2022-06-06"]:
    for k in range(-21, 22):
        dt = e + pd.Timedelta(days=k)
        if dt in tc.index:
            rows.append({"k": k, "gap": tc.loc[dt, "gap"], "eid": e.year})
ev = pd.DataFrame(rows)
if len(ev):
    avg = ev.groupby("k").gap.mean().rolling(3, center=True, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(avg.index, avg.values, lw=1.8, color="#4527a0")
    ax.axvspan(-4, 5, color="red", alpha=0.12, label="jendela jeda gage")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("hari relatif terhadap Idul Fitri")
    ax.set_ylabel("NO2 treated - control (umol/m2, MA-3)")
    ax.set_title("Gap koridor vs kontrol sekitar Lebaran (rata-rata 2023-2026)")
    ax.legend()
    fig.tight_layout(); fig.savefig(PROC + "m4_event_lebaran.png", dpi=150)
    print("\nplot: m4_event_lebaran.png")
    print("Cara baca: lembah dalam jendela merah = Jakarta kosong (mudik). "
          "Pertanyaannya ada di TEPI jendela: apakah gap pulih lebih lambat/"
          "cepat dari pola mudik murni.")
