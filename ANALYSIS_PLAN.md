# ANALYSIS PLAN — Evaluasi Kausal Kebijakan Ganjil-Genap terhadap Polusi Udara Jakarta

Dokumen ini adalah pre-registration internal: keputusan desain, spesifikasi model, dan hasil dicatat SEBELUM/SAAT diperoleh, agar analisis tidak menyimpang mengikuti hasil yang "enak". Hasil tidak pernah dihapus atau direvisi — perubahan dicatat sebagai entri baru dan diringkas di Changelog.

**Lokasi:** root project (`ANALYSIS_PLAN.md`)
**Dokumen pendamping:** `SOURCES.md` (provenans data), `README.md` (pintu masuk project)
**Terakhir diperbarui:** 2026-07-29
**Status:** analisis kausal selesai; verdict final = **tidak konklusif (null)**. Tahap berikutnya: pelaporan.

---

## 1. Pertanyaan Riset

**Pertanyaan awal:** Apakah kebijakan ganjil-genap (gage) secara kausal menurunkan polusi udara Jakarta?

**Pertanyaan setelah reframing (lihat H9):** Dapatkah efek gage diukur secara kredibel dengan data observasional yang tersedia — dan apa yang dibutuhkan agar bisa?

- **Outcome utama:** NO2 — paling spesifik bersumber dari knalpot kendaraan.
- **Outcome placebo:** SO2 (O3 dikeluarkan, lihat D7).
- **Outcome sekunder:** PM2.5, PM10.
- **Tidak dipakai sebagai outcome:** `ispu_max` (definisi berubah antar era, temuan #7).
- **Intervensi utama:** reaktivasi/ekspansi penuh 25 ruas, **6 Juni 2022**.
- **Unit analisis:** (a) stasiun SPKU × hari; (b) sel grid TROPOMI 3,5 km × hari; ~~(c) stasiun × jam~~ — ditutup, lihat D9.

---

## 2. Kronologi Kebijakan

Variabel treatment; sumber lengkap dengan URL di `data/raw/calendar/gage_schedule.csv`.

| Periode | Status | Ruas |
|---|---|---|
| 2019-09-09 – 2020-03-15 | ON | 25 |
| 2020-03-16 – 2020-08-02 | OFF (COVID) | 0 |
| 2020-08-03 – 2020-09-13 | ON (PSBB transisi) | 25 |
| 2020-09-14 – 2021-08-11 | OFF (PSBB ketat/PPKM) | 0 |
| 2021-08-12 – 2021-10-24 | ON_PARTIAL (jam 06–20) | 8 (→3, tanggal transisi belum diverifikasi) |
| 2021-10-25 – 2022-06-05 | ON_PARTIAL | 13 |
| 2022-06-06 – 2026-03-17 | ON | 25 |
| 2026-03-18 – 2026-03-24 | OFF (Nyepi+Idulfitri) | 0 |
| 2026-03-25 – sekarang | ON | 25 |

**Catatan penting:** 6 Juni 2022 adalah transisi **13 → 25 ruas**, bukan 0 → 25. Ekspektasi besaran efek di titik ini harus moderat.

**Aturan harian:** gage hanya hari kerja, bukan libur nasional/cuti bersama (`gage_on` = regime aktif ∧ hari kerja ∧ bukan libur).

---

## 3. Data

| Dataset | Sumber | Cakupan | Peran | Status |
|---|---|---|---|---|
| Panel stasiun harian (FINAL) | Satu Data Jakarta + scraping rendahemisi | 2019–2025, 5 stasiun, 12.040 baris | ITS, outcome utama | ✔ |
| Per jam 2022 | rendahemisi.jakarta.go.id (SILIKA DLH) | 13 Jan–31 Des 2022, 42.720 baris | Penambal bolong 2022; deskriptif | ✔ (dimensi jam ditutup, D9) |
| Citywide harian | Satu Data Jakarta | 2022, 364 baris | Cadangan/cross-check | ✔ (file mentah 2019–2020 tertimpa) |
| TROPOMI NO2 | GEE `COPERNICUS/S5P/OFFL/L3_NO2` | 2019–Jul 2026, 156 sel | DiD spasial (tulang punggung) | ✔ |
| Cuaca per jam | Open-Meteo archive | 2019–Jul 2026, 5 titik | Kovariat (analisis stasiun) | ✔ |
| Libur nasional | library `holidays` | 2019–2026, 134 hari | Kalender | ✔ |
| Jadwal gage | riset pemberitaan (bersumber) | 2019–2026, 9 periode | Treatment | ✔ |
| Ruas gage GeoJSON | v0 aproksimasi (±100–400 m) | 25 ruas | Klasifikasi treated | ✔ (v1 OSM menyusul) |
| Koordinat SPKU | aproksimasi ±200 m | 5 stasiun | Geo | ✔ (verifikasi menyusul) |
| Google Mobility | google.com/covid19/mobility | 2020–Okt 2022 | Kovariat COVID (opsional) | ✔ diunduh & difilter, belum dipakai sebagai kovariat |
| PPID DLH (konsentrasi µg/m³ per jam) | permohonan resmi | — | Pengganti indeks ISPU | ✖ **tidak memperoleh respons dalam periode penelitian** |

### Temuan kualitas data

Semua penanganan tercatat di kolom `dq_flag` pada panel final; reparasi terdokumentasi di `scripts/build_ispu_panel.py`.

1. **Panel stasiun 2022 tidak diterbitkan portal** → bolong Jan–Nov 2022 ditambal dari scraping per jam (agregat harian, 1.406 stasiun-hari, flag `from_hourly_scrape`). Validasi vs data resmi pada periode tumpang tindih (Des 2022, n=102 stasiun-hari): korelasi 0,978–0,999 (NO2: 0,996), bias ≈ 0. **Tambalan setara resmi.**
2. **File 2020 korup:** seluruh Maret kehilangan identitas stasiun (155 baris, tidak dapat dipulihkan; flag `station_unrecoverable_mar2020`), Juni & November bolong parah (duplikat hari; sisa hari hilang), format tanggal campur (ISO/D-M) dan salah ketik tahun.
3. **Episode anomali Okt–Nov 2020:** kelima stasiun serempak melonjak 4–10× lalu pulih — dikonfirmasi artefak (bukan polusi). Baris 2020-10-01 s.d. 2020-12-15 di-flag `anomaly_ispu_transition_2020` (325 baris), dikeluarkan dari estimasi.
4. **Diskontinuitas skala ISPU** (dugaan kuat: implementasi Permen LHK 14/2020): NO2 rata-rata era 2019–Sep 2020 = 9,6 (SD 4,0) vs era 2021+ = 21,9 (SD 13,5), naik ~2,3×. **Wasit TROPOMI:** NO2 kolom 2019 = 93,9 vs 2021 = 91,9 µmol/m² (datar) → penggandaan adalah artefak skala, bukan polusi. Konsekuensi: perbandingan level indeks lintas-era DILARANG (→ D1).
5. **TROPOMI:** coverage 30% (masking awan; kemarau ~48%, hujan ~20%); missing tidak diimputasi; nilai negatif kecil (0,1%) dipertahankan sebagai noise retrieval normal.
6. **Kepadatan per jam 2022:** 62% stasiun-jam terisi; jam gage tercakup baik (06–10: 65–69%; 16–21: 70–74%); dini hari 00–02 buruk (15%). Arsip mulai 13 Jan 2022 (1–12 Jan tidak tersedia).
7. **`ispu_max` tidak konsisten** dengan maksimum kolom polutan pada 2,6% baris: `critical_param` sering menunjuk PM2.5 yang tidak diterbitkan sebagai kolom pada 2019–2020 (PM2.5 tersedia 0% di 2019–2020, 95%+ sejak 2021). Bukan korupsi, tetapi **`ispu_max` tidak dipakai sebagai outcome**.
8. **Data "per jam" adalah indeks berbasis rata-rata bergerak, bukan konsentrasi sesaat.** Bukti: korelasi jam *t* vs *t+1* dalam hari yang sama = **0,997**; variasi dalam-hari hanya **0,165×** variasi antar-hari; amplitudo profil rata-rata NO2 sepanjang hari **0,92 poin** (~5% dari level); dan yang menentukan — **profil O3 rata dan terbalik secara fotokimia** (puncak pukul 03.00, minimum 17.00), padahal ozon secara fisik harus memuncak tengah hari. Konsisten dengan definisi ISPU yang dihitung dari rata-rata bergerak (PM 24 jam, CO 8 jam, dst.). **Konsekuensi: dimensi jam tidak dapat digunakan untuk identifikasi** (→ D9). Tidak memengaruhi tambalan harian 2022, yang tervalidasi terhadap angka resmi (r=0,996).

**Pola missing panel stasiun:** 147–157 hari hilang per stasiun (~6% kalender), terkonsentrasi di Maret 2020, Juni 2020, November 2020, dan 1–12 Januari 2022 — seluruhnya di luar jendela intervensi. Jendela Mei–Juli 2022 terisi penuh (425 dari 460 stasiun-hari, NO2 100% terisi).

---

## 4. Keputusan Desain (terkunci)

- **D1.** ITS berbasis indeks stasiun dibatasi **era metodologi konsisten (2021+)**; lintas-era hanya via TROPOMI.
- **D2.** DiD spasial memakai TROPOMI; klasifikasi sel: 16 treated (memotong ruas gage; 10 fase-13, 5 keduanya, 1 hanya-baru), 132 kontrol, 8 buffer (<2 km, tak memotong) dikeluarkan.
- **D3.** Desain "ekspansi 13→25" sebagai kontras spasial **dibatalkan** (hanya 1 sel murni ruas-baru); dialihkan ke event study temporal.
- **D4.** Missing outcome tidak diimputasi; panel tak seimbang ditangani FE.
- **D5.** Tambalan/reparasi selalu ber-flag; robustness wajib: hasil stabil tanpa baris ber-flag.
- **D6.** Definisi `gage_aktif` untuk data satelit (lintas ~13.30 WIB): 1 pada hari kerja ber-rezim aktif (emisi sesi pagi masih membekas), 0 lainnya.
- **D7.** O3 **dikeluarkan** dari placebo outcome (terkopel kimiawi dengan NO2 via NOx titration). Placebo = SO2; PM10/PM2.5 sekunder, bukan placebo.
- **D8.** Desain M4 (event study jeda libur) **dikeluarkan** dari desain utama — jeda gage kolinear sempurna dengan libur panjang/mudik. Dilaporkan sebagai limitasi identifikasi, bukan hasil.
- **D9.** Seluruh desain berbasis **dimensi jam ditutup permanen** (bukan ditunda). Alasan utama: data per jam adalah indeks ber-smoothing sehingga tidak membedakan jam (temuan #8); alasan kedua: tidak ada variasi treatment pada stasiun near. M2 v1 diperlakukan sebagai deskriptif; M2 v2 dan scraping per jam 2023 dibatalkan.
- **D10.** Spesifikasi utama DiD spasial dinaikkan ke versi R1: **outcome log, kontrol dibatasi cincin ≤15 km** (versi level dipertahankan sebagai pembanding).
- **D11.** Klaim final wajib disertai hasil **randomization inference** (M6); tanpa itu, temuan hanya boleh dilaporkan sebagai sugestif.
- **D12.** Setelah H9: **klaim kausal ditarik.** Pelaporan memakai framing "batas identifikasi", dan setiap p-value konvensional wajib didampingi RI p-value.

---

## 5. Spesifikasi Model

| Kode | Desain | Status | Script |
|---|---|---|---|
| M1 | Triple difference spasial (TROPOMI) | dijalankan — spesifikasi utama | `did_first.py` |
| M2 | Triple-diff per jam (stasiun, 2022) | dijalankan → deskriptif (D9) | `hourly_triplediff.py` |
| M3 | ITS stasiun era-konsisten (2021+) | dijalankan | `its_main.py` |
| M4 | Event study sakelar (jeda libur) | dijalankan → dibatalkan (D8) | `event_study_switches.py` |
| M5 | Paket uji ketahanan (11 uji) | dijalankan | `robustness.py` |
| M6 | Randomization inference | dijalankan — penentu verdict | `randomization_inference.py` |

**M1.** `umol ~ treated:workday + treated:regime_on + treated:workday:regime_on | cell_id + date`, cluster SE per sel. Versi utama (D10): outcome log, kontrol cincin ≤15 km.

**M2.** Kontras jam-gage (06–10, 16–21) vs jam siang (11–15) × hari kerja vs akhir pekan/libur; FE stasiun + FE tanggal; placebo jam malam.

**M3.** NO2 ~ tren + level shift + slope change di 2022-06-06 + harmonik musiman (2 orde) + dummy hari + libur + Ramadan/mudik + cuaca; SE Newey-West lag 14. Estimasi naif dilaporkan sebagai pembanding yang "dibantah".

**M5.** Placebo tanggal; placebo outcome; pre-trend; sensitivitas jendela; tanpa baris ber-flag; kontrol cincin; agregasi mingguan; log vs level.

**M6.** (a) ITS pada 37 tanggal intervensi fiktif; (b) DiD dengan label treated dipermutasi antar sel — versi acak murni dan versi acak-terkluster-spasial (menjaga struktur kluster koridor).

---

## 6. Hasil (kronologis, apa adanya)

**H1 — DiD naif `treated:gage_on` (2019–2026):** +12,76 (SE 1,42) — TERTOLAK sebagai kausal.

**H2 — Placebo rezim-OFF `treated:fake_on`:** +24,07 (SE 2,06) — "efek" lebih besar saat kebijakan tidak eksis → H1 terkontaminasi efek-hari-kerja pusat kota. Placebo bekerja sebagaimana dirancang; spesifikasi dipindah ke triple difference (M1).

**H3 — M1 Triple difference (2019–2026, n=144.679):**
- `treated:workday` = **+16,72** (SE 1,92) — lonjakan hari-kerja alami koridor.
- `treated:regime_on` = +9,38 (SE 1,81) — komposisi era (rezim-ON ≈ era normal, OFF ≈ COVID).
- **`treated:workday:regime_on` = −2,82 (SE 1,70; p=0,100; CI [−6,18; +0,55])** — estimasi awal efek kebijakan: pemangkasan ~17% dari lonjakan-hari-kerja koridor (~2% dari level pusat kota). Arah sesuai hipotesis; presisi borderline.

**H4 — Pembanding era-ON penuh (2022+):** `treated:workday` = +15,10 (SE 1,53).

**H5 — M2 v1 Triple-diff per jam (2022, n=1.413 stasiun-hari):**
`workday:near` = +0,047 (SE 0,098; p=0,63; CI [−0,15; +0,24]); sub-periode 13-ruas −0,025 (p=0,86); sub-periode 25-ruas +0,124 (p=0,38); placebo jam malam (22–02) −0,250 (p=0,34).
*Interpretasi (direvisi setelah temuan #8):* nol presisi ini **bukan bukti efek nol**, melainkan konsekuensi alat ukur. Dua alasan, berurutan menurut kefatalannya: (a) **data per jam ter-smoothing** — korelasi jam *t* vs *t+1* = 0,997 dan profil O3 terbalik secara fotokimia, sehingga kontras jam-gage vs jam-siang secara struktural tidak dapat dideteksi; (b) **tidak ada variasi treatment** — DKI1 (Thamrin) berada di ruas gage sepanjang 2022 (bagian dari 13 ruas sejak Okt 2021), sehingga kontras mencampur lonjakan-komuter pusat kota (+) dengan penekanan gage (−) yang dapat saling meniadakan. **Deskriptif, bukan uji kebijakan.** Produk yang tetap berguna: `m2_hourly_profile.png`. Jarak stasiun ke ruas gage: DKI1 0,0 km; DKI5 2,6; DKI2 5,2; DKI3 5,6; DKI4 6,6 km.

**H6 — M4 Event study jeda libur (TROPOMI, 2022-06-06+, n=81.685):**
`treated:workday` = +16,23 (SE 1,65); **`treated:pause_workday` = −26,66 (SE 2,85; p<0,001)** — arah berlawanan dengan hipotesis.
*Interpretasi:* jeda gage **kolinear sempurna** dengan libur panjang/mudik; efek pengosongan kota (koridor komuter paling terdampak) mengubur efek kebijakan. Tidak ada jeda gage di luar libur, dan tidak ada libur panjang tanpa jeda gage di era normal (Lebaran 2020/2021 = larangan mudik, pola berbeda). **Desain dinyatakan tidak dapat mengidentifikasi efek kebijakan.**

**H7 — M3 ITS era-konsisten (2021-01-01 s.d. 2025-11-30, rata-rata kota, HAC lag 14):**
- Estimasi **naif** sebelum-vs-sesudah: **+4,52 poin (+24,3%)** (jendela ±6 bulan: +0,67).
- **Level shift (`post`) = −3,35 poin (SE 1,14; p=0,003; CI [−5,59; −1,11]).**
- **Slope change (`t_post`) = +0,41 poin per 30 hari (p<0,001)** → penurunan terkikis; 3,35 ÷ 0,41 ≈ **8 bulan** sampai efek habis (terlihat pada `m3_its_counterfactual.png`: counterfactual menyeberang aktual dan berada di bawahnya sejak 2024).
- Koefisien fisik konsisten: angin −1,08 (p<0,001), hujan −0,093 (p=0,001), libur −2,03 (p=0,009), Senin–Jumat +1,76…+2,49 di atas Minggu.
*Interpretasi:* pola "turun tajam lalu merangkak naik" sejalan dengan literatur pembatasan plat nomor (Mexico City *Hoy No Circula*, Beijing) dan mekanisme adaptasi rumah tangga (kendaraan kedua berplat komplementer). Arah bias mendukung: pemulihan lalu lintas pasca-COVID seharusnya membias `post` ke POSITIF.
*Konvergensi:* M1 (−2,82) dan M3 (−3,35) searah meski data, unit, dan sumber bias berbeda.

**H8 — M5 Paket uji ketahanan** (`m5_robustness_summary.csv`):

| Uji | Koef | SE | p | Putusan |
|---|---|---|---|---|
| M1 baseline (level) | −2,816 | 1,702 | 0,100 | borderline |
| **R1 log + cincin ≤15 km** | **−0,029** | 0,010 | **0,006** | efek −2,9% proporsional, signifikan |
| R2 mingguan (`treated:regime_on`) | +3,508 | 1,886 | 0,065 | kontras rezim saja; tidak sebanding |
| R5 pre-trend (`treated:t`/30 hari) | −0,650 | 0,403 | 0,109 | netral |
| R7a jendela 2019–2023 | −3,957 | 1,698 | 0,021 | konsisten baseline |
| **R7b jendela 2021–2026** | **−14,001** | 3,154 | <0,001 | **LAMPU KUNING — estimasi meledak 5×** |
| ITS baseline (level shift NO2) | −3,349 | 1,143 | 0,003 | referensi |
| R3a placebo O3 | +3,997 | 1,851 | 0,031 | bukan kegagalan — lihat catatan |
| R3b placebo SO2 | +0,784 | 1,488 | 0,598 | LOLOS |
| **R4 placebo tanggal (2021-09-01)** | **−2,755** | 1,711 | 0,108 | **LAMPU KUNING — besaran ≈ efek asli** |
| R6 ITS tanpa baris ber-flag | −4,849 | 4,614 | 0,293 | arah sama, presisi hancur |

*Catatan R3a (NOx titration):* kenaikan O3 saat NO2 turun adalah fenomena kimia atmosfer terdokumentasi — NO menghancurkan O3, sehingga penurunan emisi NOx justru menaikkan ozon permukaan (dilaporkan luas pada studi pembatasan lalu lintas dan periode lockdown COVID). O3 **terkopel kimiawi dengan outcome utama dan tidak sah sebagai placebo** (→ D7).

*Catatan R7b:* pada jendela 2021–2026, satu-satunya periode rezim-OFF adalah Jan–Agu 2021 (PPKM) dan jeda Mar 2026, sehingga kontras nyaris seluruhnya "era COVID vs era normal", bukan "gage mati vs hidup". Identifikasi M1 bergantung pada periode OFF mana yang masuk sampel — dan **seluruh periode OFF terkontaminasi**.

**H9 — M6 Randomization inference** (`m6_randomization_inference.csv`) — **PENENTU VERDICT**:

| Uji | Efek asli | n perm | RI p | Persentil |
|---|---|---|---|---|
| RI-A ITS tanggal fiktif | −3,349 | 37 | **0,730** | 27 |
| RI-B DiD permutasi spasial-terkluster | −0,0287 (log) | 100 | **0,500** | 26 |
| RI-B DiD permutasi acak murni | −0,0287 (log) | 100 | 0,060 | 3 |

*Interpretasi:*
- **RI-A:** deret NO2 harian cukup bergelombang sehingga ITS "menemukan" level shift ±3 poin di tanggal mana pun. ITS pada deret ini **tidak informatif**. Mengkonfirmasi R4 dengan 37 titik, bukan satu.
- **RI-B spasial:** gugus treated palsu berukuran sama di lokasi acak (tetap terkluster) menghasilkan koefisien seekstrem efek asli pada separuh permutasi. Pola tersebut **bukan khas koridor gage**. Terlihat pada `m6_ri_did.png`: distribusi permutasi spasial melebar (−0,06…+0,08) sementara permutasi acak menyempit di sekitar nol; efek asli jatuh di tengah massa distribusi spasial.
- **Temuan metodologis:** p-value untuk koefisien yang sama = 0,006 (cluster-robust) vs 0,060 (permutasi acak) vs 0,500 (permutasi spasial). Permutasi acak menghancurkan korelasi spasial → distribusi null terlalu sempit → inferensi terlalu optimistis. Demonstrasi kuantitatif bahwa **inferensi konvensional pada data spasial beresolusi tinggi bersifat anti-konservatif**.

### VERDICT FINAL (2026-07-29)

**Efek ganjil-genap terhadap NO2 tidak dapat diidentifikasi secara kredibel dengan data yang tersedia.** Bukan "tidak ada efek", melainkan "tidak dapat dibedakan dari nol dengan desain observasional yang tersedia".

**Akar masalah (struktural, bukan spesifikasi):** setiap periode gage mati berimpit dengan pandemi (2020–2021) atau libur panjang/mudik (2023–2026). Tidak pernah ada kondisi "gage mati, kota normal".

- **Bahasa klaim yang diizinkan:** "estimasi menunjukkan penurunan ~3%, namun tidak dapat dibedakan dari efek palsu pada uji randomization inference (RI p = 0,50); temuan dilaporkan sebagai null/tidak konklusif."
- **Bahasa yang DILARANG:** "terbukti menurunkan", "efektif", "signifikan menurunkan polusi", angka tunggal tanpa RI p-value.

**Skor desain:** dari 4 desain yang diuji — M1 (estimasi ada, gagal RI), M2 (alat ukur tidak mampu), M3 (estimasi ada, gagal RI), M4 (terkonfound total) — **tidak satu pun menghasilkan identifikasi yang kredibel.**

---

## 7. Limitasi

**Batas identifikasi (utama):**
- **Seluruh periode rezim-OFF terkontaminasi:** OFF panjang berimpit pandemi, OFF pendek berimpit mudik. Batas struktural, bukan kelemahan spesifikasi (terlihat pada R7b, H6, H9).
- **Sensitivitas jendela waktu tinggi** (R7b): estimasi bergantung komposisi periode OFF dalam sampel.
- **Placebo tanggal tidak bersih** (R4, RI-A): ITS menemukan level shift serupa di tanggal sembarang.
- **Variasi spasial stasiun darat terlalu tipis** (1 dari 5 stasiun di koridor gage).
- **Inferensi konvensional anti-konservatif** pada struktur spasial ini (H9).
- **Intervensi utama bukan on/off**, melainkan ekspansi 13→25 ruas di atas basis yang sudah ter-treatment.

**Batas pengukuran:**
- Outcome stasiun = indeks ISPU (bukan µg/m³); konversi monoton → arah efek sahih, besaran dalam poin indeks. Permohonan PPID untuk konsentrasi tidak memperoleh respons.
- **Dimensi jam tidak tersedia secara efektif:** data per jam yang dipublikasikan adalah indeks ber-rata-rata bergerak (temuan #8), menutup seluruh kelas desain intra-hari.
- `ispu_max` tidak dapat dipakai sebagai outcome (definisi berubah antar era, temuan #7).
- TROPOMI: kolom troposferik ≠ konsentrasi permukaan; lintas ~13.30 WIB (di luar sesi gage pagi); resolusi 3,5 km mencampur jalan gage & non-gage; missing berkorelasi hujan (bias simetris treated/control).
- O3 tidak dapat dipakai sebagai placebo (kopel kimiawi NOx–O3).
- GeoJSON ruas v0 aproksimasi ±100–400 m; koordinat SPKU ±200 m.
- Transisi 8→3 ruas (Agu–Okt 2021) belum terverifikasi tanggalnya.
- Google Mobility tersedia, belum dimasukkan ke M3.

**Batas cakupan:**
- Gage mungkin memindahkan lalu lintas ke jalan alternatif tak terpantau (spillover); buffer 2 km memitigasi sebagian.

---

## 8. Reproduksi

```
data mentah (lihat SOURCES.md)
  └─ build_ispu_panel.py    → panel stasiun, per jam bersih, citywide
     └─ build_master_panel.py → master panel + 3 plot EDA
        └─ classify_cells.py  → klasifikasi sel + peta desain
           └─ did_first.py · hourly_triplediff.py · its_main.py
              · event_study_switches.py · robustness.py
              · randomization_inference.py
```

Jalankan seluruhnya: `python run_all.py` (9 script, ±85 detik).
Ekspor TROPOMI (`scripts/gee_tropomi_export.js`) dijalankan terpisah di Earth Engine Code Editor.
Dependensi ter-pin di `requirements.txt`; seluruh angka pada Bagian 6 dihasilkan di lingkungan tersebut.

**Verifikasi reproduksi (2026-07-29):** pipeline dijalankan penuh dari file mentah; seluruh koefisien H1–H9 identik sampai desimal ketiga.

---

## 9. Rencana Berikutnya

1. **(Opsional) Desain gradien jarak** — pintu identifikasi terakhir: uji apakah efek meluruh mulus terhadap jarak ke ruas gage (prediksi fungsional spesifik, sulit dipalsukan kebetulan), dengan RI berbasis permutasi permukaan jarak. *Ekspektasi: null juga, karena masalahnya variasi temporal, bukan bentuk fungsional paparan.*
2. **Finalisasi pelaporan** dengan framing baru. Kontribusi: (a) infrastruktur data tervalidasi silang, termasuk deteksi diskontinuitas metodologi ISPU lewat pembanding satelit dan deteksi smoothing pada data per jam; (b) pemetaan sistematis mengapa tiap desain gagal teridentifikasi di konteks Jakarta; (c) demonstrasi kuantitatif divergensi antar metode inferensi.
3. **Dashboard Streamlit:** plot counterfactual, tabel lintas desain, panel placebo + randomization inference.
4. **README.md** — pintu masuk project (pertanyaan, data, temuan, verdict, cara reproduksi).
5. Ganti GeoJSON v0 → v1 OSM dan verifikasi koordinat SPKU; estimasi ulang untuk memastikan hasil tidak bergantung geometri aproksimasi.
6. Unduh Google Mobility; masukkan sebagai kovariat M3.
7. **Rekomendasi riset lanjutan** (bagian diskusi): data yang dibutuhkan agar pertanyaan ini terjawab — konsentrasi µg/m³ **sesaat** (bukan rata-rata bergerak) per jam, data volume lalu lintas per ruas, atau variasi kebijakan yang tidak berimpit libur/pandemi.
8. Opsional: menjelaskan divergensi pasca-2022 (TROPOMI turun 94→85, indeks stasiun naik).

---

## Changelog

- **2026-07 (a).** Tahap 0–1 selesai (pengumpulan + cleaning + EDA). Temuan kualitas data #1–6. Keputusan D1–D6. Hasil H1–H4. Dokumen dibuat.
- **2026-07 (b).** M2 v1, M4, M3, M5 dijalankan. Hasil H5–H8. Keputusan D7–D11. M4 dan M2 v2 dibatalkan karena masalah identifikasi. Spesifikasi utama dinaikkan ke log+cincin. Verdict sementara: sugestif.
- **2026-07 (c).** M6 randomization inference dijalankan. Hasil H9. Keputusan D12. **Klaim kausal ditarik; verdict final = null/tidak konklusif.** Pertanyaan riset di-reframe ke batas identifikasi.
- **2026-07 (d).** Pipeline direproduksi penuh lewat `run_all.py` (9 script, 83 detik); seluruh angka H1–H9 identik. Audit panel final menemukan temuan kualitas data #7 dan #8. D9 diperkuat: desain berbasis jam ditutup permanen. Interpretasi H5 direvisi. Verdict final tidak berubah.
- **2026-07 (e).** Perapian dokumen: status PPID diperbarui (tidak memperoleh respons), tabel data diberi kolom status, Bagian 5 diringkas jadi tabel, Bagian 8 (Reproduksi) ditambahkan, pola missing panel didokumentasikan, skor desain ditambahkan ke verdict.
- **2026-07 (f).** Koefisien M1/M2/M3 disimpan ke CSV (4 file baru di `data/processed/`). README.md, app.py (dashboard Streamlit), dan repositori git dibuat. Google Mobility diunduh dan difilter.