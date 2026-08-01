# Apakah Ganjil-Genap Menurunkan Polusi Udara Jakarta?

Evaluasi kausal kebijakan pembatasan plat nomor (ganjil-genap) terhadap konsentrasi NO2
di DKI Jakarta, 2019–2026, menggunakan data stasiun pemantau darat dan satelit Sentinel-5P.

**Jawaban singkat: tidak dapat dijawab secara kredibel dengan data yang tersedia — dan
project ini mendokumentasikan secara sistematis mengapa.**

---

## Pertanyaan dan mengapa ini sulit

Membandingkan polusi sebelum dan sesudah kebijakan hampir pasti menyesatkan: polusi Jakarta
bergerak karena musim hujan, akhir pekan, libur panjang, pemulihan pasca-COVID, dan tren
kendaraan — semuanya tanpa peduli ada kebijakan atau tidak. Menjawab pertanyaan ini berarti
memperkirakan sesuatu yang tidak pernah terjadi: seperti apa udara Jakarta *seandainya*
kebijakan tidak pernah diberlakukan. Itu counterfactual, dan harus dibangun.

Empat desain kausal diuji untuk membangunnya. Tidak satu pun bertahan.

## Temuan utama

| # | Temuan |
|---|---|
| 1 | **Alat ukur pernah berganti skala tanpa pengumuman.** Level indeks ISPU era 2021+ ≈ 2,3× era 2019–2020 (9,6 → 21,9). Dibuktikan artefak dengan pembanding satelit: TROPOMI NO2 2019 = 93,9 vs 2021 = 91,9 µmol/m² (datar). Konsekuensi: perbandingan level lintas-era tidak sah. |
| 2 | **Data "per jam" yang dipublikasikan bukan konsentrasi sesaat**, melainkan indeks ber-rata-rata bergerak. Bukti: korelasi jam *t* vs *t+1* = 0,997; profil O3 terbalik secara fotokimia (puncak 03.00, minimum 17.00). Seluruh kelas desain intra-hari tertutup. |
| 3 | **Estimasi awal menunjukkan penurunan ~3%** (DiD spasial −2,9%, p=0,006; ITS −3,35 poin, p=0,003), searah pada dua desain independen, dengan pola "turun lalu terkikis dalam ~8 bulan" yang sejalan literatur Mexico City dan Beijing. |
| 4 | **Namun temuan itu tidak lolos randomization inference.** Intervensi fiktif di 37 tanggal acak menghasilkan efek sebesar itu (RI p=0,730); gugus treated palsu di lokasi acak juga (RI p=0,500). Klaim kausal ditarik. |
| 5 | **Temuan metodologis:** p-value untuk koefisien yang sama = 0,006 (cluster-robust) vs 0,060 (permutasi acak) vs 0,500 (permutasi yang menghormati struktur spasial). Inferensi konvensional pada data spasial beresolusi tinggi bersifat anti-konservatif. |

**Akar masalahnya struktural:** setiap periode ganjil-genap dimatikan berimpit dengan
pandemi (2020–2021) atau libur panjang/mudik (2023–2026). Tidak pernah ada kondisi
"gage mati, kota normal" — tanpa variasi itu, tidak ada desain observasional yang menolong.

## Data

| Sumber | Cakupan | Peran |
|---|---|---|
| ISPU stasiun SPKU (Satu Data Jakarta) | 2019–2025, 5 stasiun, 12.040 baris | outcome utama |
| Scraping rendahemisi.jakarta.go.id | 13 Jan–Des 2022, 42.720 baris per jam | penambal bolong 2022 |
| Sentinel-5P TROPOMI NO2 (Earth Engine) | 2019–Jul 2026, 156 sel grid 3,5 km | DiD spasial |
| Open-Meteo | 2019–2026, 5 titik, per jam | kovariat cuaca |
| Jadwal gage (riset pemberitaan) | 9 periode on/off 2019–2026 | variabel treatment |
| Google Mobility, kalender libur, geometri ruas | — | kovariat & klasifikasi |

Portal tidak pernah menerbitkan panel per-stasiun untuk 2022 — persis tahun intervensi.
Bolong itu ditambal lewat scraping data per jam, lalu **divalidasi terhadap data resmi**
pada periode tumpang tindih (n=102 stasiun-hari): korelasi 0,978–0,999, bias ≈ 0.

Provenans lengkap: [`SOURCES.md`](SOURCES.md).

## Metode

| Kode | Desain | Hasil |
|---|---|---|
| M1 | Triple difference spasial (TROPOMI, FE sel + FE tanggal) | −2,9% (p=0,006) → gagal RI |
| M2 | Triple-diff per jam (stasiun, 2022) | nol; alat ukur tidak mampu |
| M3 | Interrupted Time Series (2021+, Newey-West) | −3,35 poin (p=0,003) → gagal RI |
| M4 | Event study jeda libur | terkonfound mudik |
| M5 | 11 uji ketahanan (placebo tanggal/outcome, pre-trend, jendela, dll.) | dua lampu kuning |
| M6 | Randomization inference (137 permutasi) | **penentu verdict** |

Catatan desain dan seluruh keputusan yang dikunci sebelum melihat hasil:
[`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md).

## Struktur project

```
├── ANALYSIS_PLAN.md          pre-registration: keputusan, spesifikasi, hasil, verdict
├── SOURCES.md                provenans tiap dataset
├── requirements.txt          dependensi ter-pin
├── run_all.py                jalankan seluruh pipeline
├── data/
│   ├── raw/                  data mentah — tidak pernah diedit
│   └── processed/            tabel analisis, tabel hasil, gambar
└── scripts/
    ├── download_*.py         pengumpul data (cuaca, kalender, mobility)
    ├── scrape_rendahemisi.py scraper ISPU per jam
    ├── gee_tropomi_export.js ekspor satelit (dijalankan di Earth Engine)
    ├── build_ispu_panel.py   pembersihan + penggabungan panel
    ├── build_master_panel.py master panel + EDA
    ├── classify_cells.py     klasifikasi sel treated/control
    └── did_first.py · hourly_triplediff.py · its_main.py
        · event_study_switches.py · robustness.py · randomization_inference.py
```

## Reproduksi

```bash
pip install -r requirements.txt
python run_all.py            # 9 script, ±85 detik
```

Ekspor satelit dijalankan terpisah: paste `scripts/gee_tropomi_export.js` ke
[Earth Engine Code Editor](https://code.earthengine.google.com), Run, lalu submit 8 task
di tab Tasks. Hasil masuk ke Google Drive → salin ke `data/raw/tropomi/`.

Diverifikasi 2026-07-29: pipeline dijalankan penuh dari data mentah, seluruh koefisien
identik dengan yang tercatat di `ANALYSIS_PLAN.md`.

## Kontribusi

1. **Infrastruktur data tervalidasi silang** untuk kualitas udara Jakarta 2019–2026,
   termasuk deteksi dua cacat pengukuran yang tidak terdokumentasi publik (pergantian
   skala indeks dan smoothing pada data per jam), keduanya terungkap lewat pembanding
   independen.
2. **Pemetaan sistematis batas identifikasi** kebijakan ganjil-genap di konteks Jakarta —
   mengapa tiap desain gagal, dan variasi apa yang harus ada agar pertanyaan ini terjawab.
3. **Demonstrasi kuantitatif** bahwa inferensi konvensional melebih-lebihkan presisi pada
   data spasial beresolusi tinggi (0,006 vs 0,500 untuk koefisien yang sama).

## Batasan

Outcome berupa indeks ISPU, bukan konsentrasi µg/m³ (permohonan data ke PPID DLH tidak
memperoleh respons). Satelit mengukur kolom troposferik pada ~13.30 WIB, di luar sesi
gage pagi. Geometri ruas masih aproksimasi ±100–400 m. Kemungkinan perpindahan lalu
lintas ke jalan alternatif tak terpantau tidak dapat diukur. Daftar lengkap ada di
`ANALYSIS_PLAN.md` Bagian 7.

## Acknowledgment

Pola URL arsip ISPU per jam ditemukan lewat repo publik
[`fataa34/scraping-data-ispu-jakarta`](https://github.com/fataa34/scraping-data-ispu-jakarta).
Data satelit: European Union/ESA/Copernicus, diakses via Google Earth Engine.
Data kualitas udara: Dinas Lingkungan Hidup DKI Jakarta.