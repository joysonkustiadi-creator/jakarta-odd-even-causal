# SOURCES — Provenans Data

Catatan asal-usul setiap dataset: dari mana diperoleh, kapan, bagaimana, dan
catatan penting untuk reproduksi. Dilengkapi saat data diunduh, bukan setelahnya.

**Konvensi:** file di `data/raw/` tidak pernah diedit. Seluruh pembersihan
dilakukan oleh script dan menghasilkan file di `data/processed/`.

---

## 1. ISPU harian per stasiun (outcome utama)

| Item | Keterangan |
|---|---|
| **Penerbit** | Dinas Lingkungan Hidup DKI Jakarta |
| **Portal** | https://satudata.jakarta.go.id (menggantikan data.jakarta.go.id yang dimigrasi) |
| **Mirror** | https://katalog.data.go.id (Portal Satu Data Indonesia) |
| **Cakupan** | 2019–2025, 5 stasiun (DKI1–DKI5) |
| **Format** | CSV dan .xls (perhatian: file .xls sebenarnya HTML, dibaca dengan `pd.read_html`) |
| **Diunduh** | [2026-07-28] |
| **Lisensi** | Data terbuka (Sifat Data: Terbuka) |

**File:**

| File di `data/raw/ispu/` | Nama dataset di portal | Isi sebenarnya |
|---|---|---|
| `ispu_2019.csv` | Stasiun Pemantau Kualitas Udara (SPKU) Tahun 2019 | per stasiun, 2019 penuh |
| `ispu_2020.xls` | Stasiun Pemantau Kualitas Udara (SPKU) Tahun 2020 | per stasiun, 2020 (cacat, lihat catatan) |
| `ispu_2021.csv` | Indeks Standar Pencemaran Udara (ISPU) Tahun 2021 | per stasiun, 2021 penuh |
| `ispu_2022.csv` | Indeks Standar Pencemaran Udara (ISPU) Tahun 2022 | **citywide** (1 baris/hari), bukan per stasiun |
| `ispu_2023.csv` | Indeks Standar Pencemaran Udara (ISPU) Tahun 2023 | per stasiun, **Des 2022 – Nov 2023** |
| `ispu_2024-2025.xls` | Data ISPU di Provinsi DKI Jakarta | per stasiun, Jan 2024 – Nov 2025 |

**Catatan penting:**

1. Portal menerbitkan **dua varian dengan nama mirip**: varian *per stasiun*
   (5 baris/hari) dan varian *citywide* (1 baris/hari, nilai maksimum se-kota).
   Untuk 2019 & 2020, varian per stasiun bernama "Stasiun Pemantau Kualitas
   Udara (SPKU) Tahun ...". Periksa jumlah baris sebelum memakai.
2. **Varian per stasiun untuk 2022 tidak pernah diterbitkan.** Sudah dicari di
   satudata, katalog.data.go.id, dan arsip GitHub pihak ketiga — semuanya
   citywide. Bolong Jan–Nov 2022 ditambal dari sumber #2.
3. File mentah citywide 2019 & 2020 **tertimpa** saat perapian folder
   (2026-07-29). Perlu diunduh ulang bila ingin reproduksi Bagian 6
   `build_ispu_panel.py` secara penuh. Simpan dengan nama eksplisit
   `ispu_citywide_2019.csv` / `ispu_citywide_2020.csv`.
4. Nilai adalah **indeks ISPU**, bukan konsentrasi µg/m³.
5. Kerusakan yang ditemukan dan ditangani (detail di `build_ispu_panel.py`):
   kolom bergeser (Maret 2020), duplikat stasiun-tanggal (Jun & Nov 2020),
   format tanggal campur, salah ketik tahun, tanggal tidak eksis (31 Sep 2025),
   nama stasiun tidak konsisten (3 ejaan untuk DKI1).

---

## 2. ISPU per jam per stasiun (penambal + data terkaya)

| Item | Keterangan |
|---|---|
| **Sumber** | https://rendahemisi.jakarta.go.id (situs resmi DLH, data SILIKA/SPKU) |
| **Pola URL** | `/ispu-detail/{id}/{slug}/{DD-MM-YYYY}` |
| **ID stasiun** | 4=dki1-bundaran-hi, 5=dki2-kelapa-gading, 6=dki3-jagakarsa, 7=dki4-lubang-buaya, 8=dki5-kebun-jeruk |
| **Cara** | scraping HTML, `scripts/scrape_rendahemisi.py` (jeda 1–2 detik antar request) |
| **Cakupan** | 13 Jan – 31 Des 2022 (arsip tidak tersedia sebelum 13 Jan 2022) |
| **Diunduh** | [2026-07-28] |
| **File** | `data/raw/ispu_hourly/rendahemisi_2022.csv` (42.720 baris) |

**Validasi kesetaraan dengan data resmi** (periode tumpang tindih Des 2022,
n=102 stasiun-hari): korelasi 0,978–0,999 per polutan (NO2: 0,996), bias
rata-rata ≈ 0. Agregat harian dari data per jam **setara** angka harian resmi.

**Kepadatan:** 62% stasiun-jam terisi. Jam gage tercakup baik (06–10: 65–69%;
16–21: 70–74%); dini hari 00–02 buruk (15–16%).

**Penemuan sumber:** pola URL diketahui dari repo publik
`fataa34/scraping-data-ispu-jakarta` (GitHub) — layak disebut di acknowledgment.

---

## 3. TROPOMI NO2 satelit (tulang punggung analisis spasial)

| Item | Keterangan |
|---|---|
| **Dataset** | `COPERNICUS/S5P/OFFL/L3_NO2` (European Union/ESA/Copernicus) |
| **Band** | `tropospheric_NO2_column_number_density` (mol/m²) |
| **Platform** | Google Earth Engine, tier Community (nonkomersial akademik) |
| **Script** | `scripts/gee_tropomi_export.js` |
| **Grid** | bounding box `[106.65, -6.40, 107.05, -6.05]`, sel 3500 m → 156 sel |
| **Cakupan** | 2019-01-01 – 2026-07-28, harian |
| **Diekspor** | [2026-07-28] |
| **File** | `data/raw/tropomi/tropomi_no2_jakarta_{2019..2026}.csv` |
| **Katalog** | https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S5P_OFFL_L3_NO2 |

**Catatan:** coverage ~30% (masking awan; kemarau ~48%, hujan ~20%); satelit
melintas ~13.30 WIB; nilai negatif kecil (0,1%) adalah noise retrieval normal
dan tidak dibuang. Grid harus identik antar tahun agar `cell_id` konsisten.

---

## 4. Cuaca

| Item | Keterangan |
|---|---|
| **Sumber** | Open-Meteo Historical Weather API (gratis, tanpa API key untuk nonkomersial) |
| **Endpoint** | https://archive-api.open-meteo.com/v1/archive |
| **Dokumentasi** | https://open-meteo.com/en/docs/historical-weather-api |
| **Variabel** | temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m, wind_direction_10m |
| **Resolusi** | per jam, timezone Asia/Jakarta |
| **Cakupan** | 2019-01-01 – 2026-07-28, 5 titik koordinat SPKU |
| **Script** | `scripts/download_weather.py` |
| **Diunduh** | [2026-07-28] |
| **File** | `data/raw/weather/DKI{1..5}_*.csv` |

**Catatan:** arah angin diagregasi ke harian dengan rata-rata vektor
(sin/cos), bukan rata-rata aritmetik — lihat `build_master_panel.py`.

---

## 5. Kalender libur nasional

| Item | Keterangan |
|---|---|
| **Sumber** | Library Python `holidays` (`holidays.Indonesia`) |
| **Cakupan** | 2019–2026, 134 hari libur |
| **Script** | `scripts/download_calendar.py` |
| **Dibuat** | [2026-07-28] |
| **File** | `data/raw/calendar/holidays_id.csv` |

**Catatan:** nama libur dalam bahasa Inggris ("Eid al-Fitr", "Day of Silence").
Cuti bersama yang diumumkan lewat SKB 3 Menteri **tidak selalu tercakup** —
untuk periode jeda gage, acuan utama adalah `gage_schedule.csv`.

---

## 6. Jadwal ganjil-genap (variabel treatment)

| Item | Keterangan |
|---|---|
| **Sumber** | Riset pemberitaan manual + Pergub DKI No. 88 Tahun 2019 |
| **Disusun** | [2026-07-29] |
| **File** | `data/raw/calendar/gage_schedule.csv` (9 periode, URL sumber per baris) |
| **Turunan** | `data/raw/calendar/gage_daily_base.csv` (harian: regime, ruas, gage_on_base) |

**Sumber utama per periode** (URL lengkap ada di kolom `source_url`):
Kompas Megapolitan (pemberlakuan 25 ruas 9 Sep 2019; penghentian 16 Mar 2020;
pemberlakuan kembali 3 Agu 2020), Detik (penghentian PSBB ketat 14 Sep 2020),
CNN Indonesia (reaktivasi 8 ruas 12 Agu 2021; perluasan 13 ruas 25 Okt 2021;
jeda Mar 2026), Korlantas Polri (25 ruas per Pergub 88/2019),
Kompas TV (jeda Nyepi–Idulfitri 2026).

**Belum terverifikasi:** tanggal transisi 8 → 3 ruas antara Agu–Okt 2021.

---

## 7. Geometri ruas gage

| Item | Keterangan |
|---|---|
| **Versi saat ini** | v0 aproksimasi (polyline manual), akurasi ±100–400 m |
| **File** | `data/raw/geo/gage_roads_v0_approx.geojson` (25 ruas) |
| **Properti** | `name`, `phase_13ruas_okt2021` (bool), `accuracy` |
| **Acuan daftar ruas** | Pergub DKI No. 88 Tahun 2019 (JDIH: https://jdih.jakarta.go.id) |
| **Versi presisi (belum)** | OpenStreetMap via https://overpass-turbo.eu, query di `data/raw/geo/overpass_query_gage_roads.txt` |

**Catatan:** akurasi v0 memadai untuk klasifikasi sel grid 3,5 km, tetapi
harus diganti v1 OSM untuk peta publikasi dan sebagai uji ketahanan geometri.

---

## 8. Koordinat stasiun SPKU

| Item | Keterangan |
|---|---|
| **File** | `data/raw/geo/stations.csv` |
| **Akurasi** | aproksimasi ±200 m — belum diverifikasi |
| **Verifikasi** | peta Lokasi SPKU di https://udara.jakarta.go.id |

---

## 9. Google Mobility (kovariat COVID) — BELUM DIUNDUH

| Item | Keterangan |
|---|---|
| **Sumber** | https://www.google.com/covid19/mobility/ (Region CSVs) |
| **File dibutuhkan** | `20{20,21,22}_ID_Region_Mobility_Report.csv` |
| **Cakupan** | Feb 2020 – Okt 2022 (program dihentikan Google) |
| **Script filter** | `scripts/filter_mobility.py` |
| **Status** | belum diunduh; opsional (kovariat pelengkap M3) |

---

## 10. PPID DLH — permohonan konsentrasi µg/m³ per jam

| Item | Keterangan |
|---|---|
| **Jalur** | https://lingkunganhidup.jakarta.go.id/layanan/ppid |
| **Diajukan** | [2026-07-28] |
| **Isi permohonan** | konsentrasi per jam (µg/m³/ppb) NO2, PM2.5, PM10, SO2, CO, O3, seluruh SPKU, 2019–2026 |
| **Status** | **tidak memperoleh respons dalam periode penelitian, dianggap data tidak lengkap dalam penelitian padahal sudah disubmit berulang kali** |

**Konsekuensi:** outcome tetap memakai indeks ISPU (besaran efek dalam poin
indeks, bukan µg/m³). Tidak memengaruhi verdict, karena keterbatasan project
bersifat identifikasi, bukan pengukuran. Dicatat di ANALYSIS_PLAN.md sebagai
limitasi dan rekomendasi riset lanjutan.

---

## 11. Sumber yang dipertimbangkan tetapi tidak dipakai

| Sumber | Alasan |
|---|---|
| Dataset Kaggle "Air Quality Index in Jakarta" | kompilasi dari portal yang sama, varian citywide — tidak menambah informasi |
| US Embassy Jakarta PM2.5 (airnow.gov) | opsional untuk validasi silang; tidak diperlukan setelah validasi rendahemisi vs portal berhasil |
| TomTom Traffic Index Jakarta | agregat tahunan, terlalu kasar untuk analisis harian |
| Copernicus Data Space (unduh TROPOMI langsung) | jauh lebih rumit daripada Google Earth Engine |

---

## Reproduksi

```
data mentah (SOURCES.md)
  └─ scripts/build_ispu_panel.py     → panel stasiun, per jam, citywide
       └─ scripts/build_master_panel.py → master panel + EDA
            └─ scripts/classify_cells.py → klasifikasi sel TROPOMI
                 └─ analisis: did_first, its_main, hourly_triplediff,
                    event_study_switches, robustness, randomization_inference
```

Dependensi: lihat `requirements.txt`. Script GEE dijalankan terpisah di
Code Editor (bukan lokal).