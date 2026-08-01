# =====================================================================
# BUILD ISPU PANEL — dari file mentah ke tabel analisis
#
# Menghasilkan 3 file di data/processed/:
#   1. ispu_station_panel_2019_2025_FINAL.csv  (tabel utama: stasiun x hari)
#   2. ispu_hourly_2022_clean.csv              (stasiun x hari x jam, 2022)
#   3. ispu_citywide_daily_2022.csv            (rekap se-kota, cadangan)
#
# Script ini mendokumentasikan SETIAP reparasi terhadap data mentah.
# Semua reparasi ditandai di kolom `dq_flag` agar dapat diaudit dan
# dikeluarkan pada uji ketahanan.
#
# CATATAN PENTING TENTANG DUA JENIS FILE:
#   - Varian PER STASIUN  : 5 baris per hari (yang kita pakai untuk panel)
#   - Varian CITYWIDE     : 1 baris per hari (rekap maksimum se-kota)
#   Portal menerbitkan keduanya dengan nama mirip. Untuk 2019 & 2020,
#   varian per stasiun bernama "Stasiun Pemantau Kualitas Udara (SPKU)".
#   Untuk 2022, varian per stasiun TIDAK PERNAH DITERBITKAN -> ditambal
#   dari hasil scraping per jam (lihat Bagian 4).
# =====================================================================
import numpy as np
import pandas as pd
from pathlib import Path

RAW = Path("data/raw")
PROC = Path("data/processed")
PROC.mkdir(parents=True, exist_ok=True)

KOLOM = ["date", "station_id", "pm10", "pm25", "so2", "co", "o3",
         "no2", "ispu_max", "critical_param", "category",
         "source_file", "dq_flag", "n_hours"]


# ---------------------------------------------------------------- utils
def tonum(s):
    """Angka dari kolom teks; penanda kosong ('-', '---') -> NaN."""
    return pd.to_numeric(
        pd.Series(s).astype(str).str.strip()
        .replace({"-": np.nan, "--": np.nan, "---": np.nan, "nan": np.nan}),
        errors="coerce")


def tanggal_berjangkar(tanggal, periode):
    """
    REPARASI TANGGAL. File mentah mencampur format (ISO, D/M/YYYY) dan
    memuat salah ketik tahun (mis. '2020-02-01' pada periode 202202).
    Kolom `periode_data` (YYYYMM) terbukti reliabel, jadi dipakai sebagai
    jangkar: hanya komponen HARI yang diambil dari kolom tanggal.
    """
    py, pm = periode // 100, periode % 100
    out = []
    for t, y, m in zip(tanggal.astype(str), py, pm):
        d = pd.to_datetime(t, format="%Y-%m-%d", errors="coerce")
        if pd.notna(d) and d.year == y and d.month == m:
            out.append(d)
            continue
        hari = None
        bagian = t.replace("-", "/").split("/")
        if len(bagian) == 3:
            try:
                a, b = int(bagian[0]), int(bagian[1])
                if b == m and 1 <= a <= 31:        # D/M/YYYY
                    hari = a
                elif a == m and 1 <= b <= 31:      # M/D/YYYY
                    hari = b
                elif pd.notna(d):                  # ISO tapi bulan salah
                    hari = d.day
            except ValueError:
                pass
        elif pd.notna(d):
            hari = d.day
        try:
            out.append(pd.Timestamp(year=y, month=m, day=hari) if hari else pd.NaT)
        except ValueError:
            out.append(pd.NaT)                     # mis. 31 September
    return pd.Series(out, index=tanggal.index)


def baca(nama):
    """File .xls dari portal sebenarnya HTML; .csv dibaca biasa."""
    p = RAW / "ispu" / nama
    return pd.read_html(p)[0] if p.suffix == ".xls" else pd.read_csv(p)


def rakit(df, kolom_map, sumber, flag=None):
    """Susun ke skema seragam. kolom_map: nama kolom sumber per polutan."""
    out = pd.DataFrame({
        "date": tanggal_berjangkar(df[kolom_map["tanggal"]], df["periode_data"]),
        "station_id": df[kolom_map["stasiun"]].astype(str).str.extract(r"(DKI\d)")[0],
        "pm10": tonum(df[kolom_map["pm10"]]),
        "pm25": tonum(df[kolom_map["pm25"]]) if kolom_map.get("pm25") else np.nan,
        "so2": tonum(df[kolom_map["so2"]]),
        "co": tonum(df[kolom_map["co"]]),
        "o3": tonum(df[kolom_map["o3"]]),
        "no2": tonum(df[kolom_map["no2"]]),
        "ispu_max": tonum(df[kolom_map["max"]]),
        "critical_param": df[kolom_map["critical"]],
        "category": df[kolom_map["kategori"]],
        "source_file": sumber,
        "dq_flag": flag,
        "n_hours": np.nan,
    })
    return out


# ============================================================ BAGIAN 1
# 2019 & 2020 — varian per stasiun ("SPKU Tahun ...")
# ---------------------------------------------------------------------
print("[1] 2019 & 2020 (varian SPKU per stasiun)")

MAP_LAMA = {"tanggal": "tanggal", "stasiun": "stasiun", "pm10": "pm10",
            "so2": "so2", "co": "co", "o3": "o3", "no2": "no2",
            "max": "max", "critical": "critical", "kategori": "categori"}

d19 = rakit(baca("ispu_2019.csv"), MAP_LAMA, "spku_2019.csv")

# REPARASI 2020-A: seluruh Maret 2020 kolomnya BERGESER satu posisi karena
# sel `stasiun` kosong di sumbernya (nilai pm10 masuk ke kolom stasiun, dst.).
# Nilai polutan dapat dipulihkan dengan menggeser balik; identitas stasiun
# TIDAK dapat dipulihkan (beberapa metode forensik dicoba, tidak konsisten)
# -> station_id = NaN, ditandai `station_unrecoverable_mar2020`.
raw20 = baca("ispu_2020.xls")
geser = ~raw20.stasiun.astype(str).str.contains("DKI")
print(f"    reparasi kolom bergeser: {geser.sum()} baris (Maret 2020)")
perbaikan = pd.DataFrame({
    "periode_data": raw20.loc[geser, "periode_data"],
    "tanggal": raw20.loc[geser, "tanggal"],
    "stasiun": np.nan,
    "pm10": raw20.loc[geser, "stasiun"], "so2": raw20.loc[geser, "pm10"],
    "co": raw20.loc[geser, "so2"], "o3": raw20.loc[geser, "co"],
    "no2": raw20.loc[geser, "o3"], "max": raw20.loc[geser, "no2"],
    "critical": raw20.loc[geser, "critical"],
    "categori": raw20.loc[geser, "categori"]})
raw20 = pd.concat([raw20[~geser], perbaikan], ignore_index=True)

d20 = rakit(raw20, MAP_LAMA, "ispu_2020.xls")
d20.loc[d20.station_id.isna(), "dq_flag"] = "station_unrecoverable_mar2020"

# REPARASI 2020-B: Juni & November memuat duplikat stasiun-tanggal (nilai
# hari salah tulis di sumber), sementara hari lain di bulan itu hilang.
# Tidak dapat direkonstruksi -> simpan kemunculan pertama, sisanya dibuang.
dup = d20.station_id.notna() & d20.duplicated(["station_id", "date"], keep=False)
print(f"    duplikat stasiun-tanggal: {dup.sum()} baris (Jun & Nov 2020)")
d20.loc[dup, "dq_flag"] = "duplicate_station_date_source"
d20 = d20[~(d20.station_id.notna()
            & d20.duplicated(["station_id", "date"], keep="first"))]


# ============================================================ BAGIAN 2
# 2021, 2023, 2024-2025 — varian per stasiun (skema kolom berbeda-beda)
# ---------------------------------------------------------------------
print("[2] 2021, 2023, 2024-2025 (varian per stasiun)")

d21 = rakit(baca("ispu_2021.csv"),
            {**MAP_LAMA, "pm25": "pm25"}, "ispu_2021.csv")

MAP_BARU = {"tanggal": "tanggal", "stasiun": "stasiun",
            "pm10": "pm_sepuluh", "pm25": "pm_duakomalima",
            "so2": "sulfur_dioksida", "co": "karbon_monoksida",
            "o3": "ozon", "no2": "nitrogen_dioksida", "max": "max",
            "critical": "parameter_pencemar_kritis", "kategori": "kategori"}

# CATATAN: file bernama "2023" sebenarnya memuat Des 2022 - Nov 2023.
d23 = rakit(baca("ispu_2023.csv"), MAP_BARU, "ispu_2023.csv")

# File 2024-2025 berbeda: tanggal disimpan sebagai tiga kolom terpisah
# (periode_data=YYYYMM, bulan, tanggal=nomor hari) -> rakit sendiri.
raw2425 = baca("ispu_2024-2025.xls")
raw2425["_tgl"] = pd.to_datetime(
    dict(year=raw2425.periode_data // 100, month=raw2425.bulan,
         day=raw2425.tanggal), errors="coerce")   # invalid (31 Sep) -> NaT
n_invalid = raw2425._tgl.isna().sum()
raw2425 = raw2425.dropna(subset=["_tgl"])
print(f"    tanggal invalid dibuang (mis. 31 September): {n_invalid} baris")
d2425 = rakit(raw2425, {**MAP_BARU, "tanggal": "_tgl"}, "ispu_2024-2025.xls")
d2425["date"] = raw2425._tgl.values     # pakai tanggal yang sudah dibentuk


# ============================================================ BAGIAN 3
# Data per jam 2022 (hasil scraping) -> file bersih + agregat harian
# ---------------------------------------------------------------------
print("[3] Data per jam 2022 (scraping rendahemisi)")

h = pd.read_csv(RAW / "ispu_hourly" / "rendahemisi_2022.csv")
h["jam"] = (h.jam.astype(str).str.extract(r"^(\d{1,2})")[0]
            .astype(int).map(lambda x: f"{x:02d}:00"))
for c in ["pm10", "pm25", "so2", "co", "o3", "no2"]:
    h[c] = tonum(h[c])
h.to_csv(PROC / "ispu_hourly_2022_clean.csv", index=False)
print(f"    -> ispu_hourly_2022_clean.csv ({len(h):,} baris; "
      f"NO2 terisi {h.no2.notna().mean()*100:.0f}%)")

h["date"] = pd.to_datetime(h.tanggal)
harian = (h.groupby(["station_id", "date"])
            .agg(pm10=("pm10", "mean"), pm25=("pm25", "mean"),
                 so2=("so2", "mean"), co=("co", "mean"), o3=("o3", "mean"),
                 no2=("no2", "mean"), n_hours=("no2", lambda s: s.notna().sum()))
            .reset_index())


# ============================================================ BAGIAN 4
# Tambalan Jan-Nov 2022 (varian per stasiun tidak pernah diterbitkan)
# Validasi kesetaraan: pada Des 2022 (tumpang tindih dgn data resmi),
# korelasi 0,978-0,999 dan bias ~0 -> agregat harian setara data resmi.
# ---------------------------------------------------------------------
print("[4] Tambalan bolong Jan-Nov 2022")

gap = harian[(harian.date >= "2022-01-01") & (harian.date <= "2022-11-30")
             & (harian.n_hours > 0)].copy()
tambalan = pd.DataFrame({
    "date": gap.date, "station_id": gap.station_id,
    "pm10": gap.pm10.round(1), "pm25": gap.pm25.round(1),
    "so2": gap.so2.round(1), "co": gap.co.round(1),
    "o3": gap.o3.round(1), "no2": gap.no2.round(1),
    "ispu_max": gap[["pm10", "pm25", "so2", "co", "o3", "no2"]].max(axis=1).round(1),
    "critical_param": np.nan, "category": np.nan,
    "source_file": "rendahemisi_2022.csv", "dq_flag": "from_hourly_scrape",
    "n_hours": gap.n_hours})
print(f"    {len(tambalan):,} stasiun-hari ditambal")


# ============================================================ BAGIAN 5
# Rakit panel final + flag anomali + verifikasi
# ---------------------------------------------------------------------
print("[5] Panel final")

panel = (pd.concat([d19, d20, d21, d23, d2425, tambalan])[KOLOM]
           .sort_values(["station_id", "date"]).reset_index(drop=True))

# FLAG ANOMALI: Okt-Des 2020 kelima stasiun serempak melonjak 4-10x lalu
# pulih. Dikonfirmasi artefak lewat pembanding TROPOMI (NO2 satelit 2019 vs
# 2021 datar: 93,9 vs 91,9 umol/m2) -> dugaan implementasi Permen LHK 14/2020.
anomali = (panel.date >= "2020-10-01") & (panel.date <= "2020-12-15")
panel.loc[anomali, "dq_flag"] = (
    panel.loc[anomali, "dq_flag"].fillna("").astype(str)
    .str.cat(pd.Series(["anomaly_ispu_transition_2020"] * anomali.sum(),
                       index=panel.index[anomali]), sep="|").str.strip("|"))
print(f"    flag anomali 2020: {anomali.sum()} baris")

diketahui = panel[panel.station_id.notna()]
assert diketahui.duplicated(["station_id", "date"]).sum() == 0, "ada duplikat!"

panel.to_csv(PROC / "ispu_station_panel_2019_2025_FINAL.csv", index=False)
print(f"    -> ispu_station_panel_2019_2025_FINAL.csv ({len(panel):,} baris)")
print("    baris per tahun:",
      {int(y): int(n) for y, n in panel.date.dt.year.value_counts().sort_index().items()})
print("    NO2 missing %/tahun:",
      {int(y): round(v) for y, v in
       panel.groupby(panel.date.dt.year).no2.apply(lambda s: s.isna().mean() * 100).items()})


# ============================================================ BAGIAN 6
# Seri citywide (varian rekap 1 baris/hari) - cadangan.
# Saat ini hanya 2022; file mentah citywide 2019 & 2020 tertimpa saat
# perapian folder. Tambahkan kembali ke daftar `kota` bila diunduh ulang.
# ---------------------------------------------------------------------
print("[6] Seri citywide (cadangan)")

kota = []
for tahun, nama in [(2022, "ispu_2022.csv")]:
    # CATATAN: varian citywide 2019 & 2020 tertimpa saat perapian folder;
    # unduh ulang dari satudata.jakarta.go.id bila ingin reproduksi penuh.
    if not (RAW / "ispu" / nama).exists():
        print(f"    lewati {nama} (tidak ada)")
        continue
    df = baca(nama)
    # REPARASI: sebagian baris 2020 kolomnya bergeser (nomor stasiun nyasar
    # ke kolom `critical`) -> kembalikan sebelum diproses.
    if "critical" in df and df["critical"].astype(str).str.fullmatch(r"[1-5]").any():
        g = df["critical"].astype(str).str.fullmatch(r"[1-5]")
        df.loc[g, "lokasi_spku"] = "DKI" + df.loc[g, "critical"].astype(str)
        df.loc[g, "critical"] = df.loc[g, "categori"]
        df.loc[g, "categori"] = np.nan
    pm10c = "pm_10" if "pm_10" in df else "pm10"
    kota.append(pd.DataFrame({
        "date": tanggal_berjangkar(df.tanggal, df.periode_data),
        "pm10": tonum(df[pm10c]),
        "pm25": tonum(df["pm_duakomalima"]) if "pm_duakomalima" in df else np.nan,
        "so2": tonum(df.so2), "co": tonum(df.co), "o3": tonum(df.o3),
        "no2": tonum(df.no2), "ispu_max": tonum(df["max"]),
        "critical_param": df.critical, "category": df.categori,
        "reporting_station": df.lokasi_spku.replace("0", np.nan),
        "source_file": nama}))
citywide = pd.concat(kota).dropna(subset=["date"]).sort_values("date")
citywide.to_csv(PROC / "ispu_citywide_daily_2022.csv", index=False)
print(f"    -> ispu_citywide_daily_2022.csv ({len(citywide):,} baris)")

print("\nSelesai. Jalankan build_master_panel.py untuk menggabungkan "
      "panel ini dengan cuaca, kalender, dan rezim gage.")
