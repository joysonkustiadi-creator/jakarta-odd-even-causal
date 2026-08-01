"""
Dashboard: Apakah Ganjil-Genap Menurunkan Polusi Udara Jakarta?

Jalankan lokal:  streamlit run app.py
Membaca dari data/processed/ dan data/raw/calendar/ — tidak menjalankan model ulang.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

PROC = Path("data/processed")
RAW = Path("data/raw")
INTV = pd.Timestamp("2022-06-06")

st.set_page_config(page_title="Ganjil-Genap & Polusi Jakarta", layout="wide")

WARNA_REZIM = {"ON": "#2e7d32", "ON_PARTIAL": "#f9a825",
               "OFF": "#c62828", "PRE": "#9e9e9e"}


# ----------------------------------------------------------------- data
@st.cache_data
def muat():
    d = {}
    d["panel"] = pd.read_csv(PROC / "master_panel_daily.csv", parse_dates=["date"])
    d["gage"] = pd.read_csv(RAW / "calendar" / "gage_schedule.csv",
                            parse_dates=["start_date", "end_date"])
    d["m1"] = pd.read_csv(PROC / "m1_coefficients.csv")
    d["m3sum"] = pd.read_csv(PROC / "m3_its_summary.csv")
    d["m5"] = pd.read_csv(PROC / "m5_robustness_summary.csv")
    d["m6"] = pd.read_csv(PROC / "m6_randomization_inference.csv")
    d["cells"] = pd.read_csv(PROC / "tropomi_cells_classified.csv")
    return d


def gambar(nama, caption=None):
    p = PROC / nama
    if p.exists():
        st.image(str(p), use_container_width=True, caption=caption)
    else:
        st.warning(f"Gambar belum tersedia: {nama} — jalankan `python run_all.py`.")


try:
    D = muat()
except FileNotFoundError as e:
    st.error(f"File hasil belum lengkap: {e}\n\nJalankan `python run_all.py` lebih dulu.")
    st.stop()


# ---------------------------------------------------------------- header
st.title("Apakah ganjil-genap menurunkan polusi udara Jakarta?")
st.markdown(
    "Evaluasi kausal kebijakan pembatasan plat nomor terhadap NO2, 2019–2026, "
    "menggunakan stasiun pemantau darat dan satelit Sentinel-5P TROPOMI."
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Perbandingan naif", "+24,3%",
          help="Rata-rata sesudah vs sebelum, tanpa kontrol apa pun.")
k2.metric("Setelah dimodelkan", "−3,35 poin", "p = 0,003",
          help="Level shift ITS dengan kontrol musim, cuaca, hari, libur.")
k3.metric("Uji randomization", "RI p = 0,50", "gagal", delta_color="inverse",
          help="Efek palsu di lokasi/tanggal acak sama besarnya.")
k4.metric("Verdict", "Null", help="Tidak konklusif — lihat tab keempat.")

st.info(
    "**Kesimpulan:** efek ganjil-genap terhadap NO2 **tidak dapat diidentifikasi "
    "secara kredibel** dengan data yang tersedia. Bukan berarti efeknya nol — "
    "melainkan tidak dapat dibedakan dari nol, karena setiap periode kebijakan "
    "dimatikan selalu berimpit dengan pandemi atau libur panjang."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Timeline", "Counterfactual", "Lintas desain", "Randomization inference"]
)


# ================================================================ TAB 1
with tab1:
    st.subheader("Tujuh tahun NO2 Jakarta, dengan sejarah kebijakan sebagai latar")

    c1, c2 = st.columns([3, 1])
    with c2:
        stasiun = st.multiselect(
            "Stasiun", sorted(D["panel"].station_id.dropna().unique()),
            default=sorted(D["panel"].station_id.dropna().unique()))
        halus = st.slider("Perataan (hari)", 1, 30, 7)
        buang_flag = st.checkbox("Sembunyikan baris bermasalah", value=True,
                                 help="Anomali Okt–Des 2020 dan baris tanpa identitas stasiun.")

    p = D["panel"]
    if buang_flag:
        p = p[~p.dq_flag.astype(str).str.contains("anomaly|unrecoverable", na=False)]
    p = p[p.station_id.isin(stasiun)]
    seri = p.groupby("date").no2.mean().rolling(halus, min_periods=1).mean()

    fig = go.Figure()
    for _, r in D["gage"].iterrows():
        fig.add_vrect(x0=r.start_date, x1=r.end_date,
                      fillcolor=WARNA_REZIM.get(r.status, "#eee"),
                      opacity=0.13, line_width=0, layer="below")
    fig.add_trace(go.Scatter(x=seri.index, y=seri.values, mode="lines",
                             line=dict(color="#1a237e", width=1.4), name="NO2"))
    fig.add_vline(x=INTV, line=dict(color="black", dash="dash", width=2),
                  annotation_text="6 Jun 2022")
    fig.update_layout(height=420, margin=dict(t=30, b=10),
                      yaxis_title="NO2 (indeks ISPU)", xaxis_title=None,
                      showlegend=False, hovermode="x unified")
    with c1:
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Latar: hijau = gage aktif, kuning = aktif sebagian, "
                   "merah = dihentikan. Garis putus-putus = reaktivasi penuh 25 ruas.")

    st.markdown("---")
    st.markdown("#### Yang terlihat di grafik ini")
    a, b, c = st.columns(3)
    a.markdown(
        "**Lompatan permanen di akhir 2020** bukan polusi, melainkan pergantian "
        "rumus indeks ISPU. Dibuktikan dengan satelit: NO2 kolom 2019 = 93,9 vs "
        "2021 = 91,9 µmol/m² — datar."
    )
    b.markdown(
        "**Tidak ada lompatan kasat mata** di 6 Juni 2022. Wajar: transisinya "
        "13 → 25 ruas, bukan dari nol. Karena itu dibutuhkan model."
    )
    c.markdown(
        "**Gelombang musiman ~10 poin** per tahun — lebih besar dari efek "
        "kebijakan yang realistis. Kontrol musiman wajib."
    )

    with st.expander("Kronologi kebijakan (9 periode, bersumber)"):
        g = D["gage"][["start_date", "end_date", "status", "ruas", "keterangan"]].copy()
        g["start_date"] = g.start_date.dt.date
        g["end_date"] = g.end_date.dt.date
        st.dataframe(g, use_container_width=True, hide_index=True)


# ================================================================ TAB 2
with tab2:
    st.subheader("Menggambar garis yang tidak pernah terjadi")
    st.markdown(
        "Untuk menilai kebijakan, kita perlu tahu seperti apa udara Jakarta "
        "*seandainya* gage tidak diperluas — **counterfactual**. Model ITS "
        "membangunnya dari tren, musim, cuaca, hari, dan libur."
    )

    s = D["m3sum"].set_index("ukuran").nilai
    c1, c2, c3 = st.columns(3)
    c1.metric("Perbandingan naif", f"{s['naif_selisih_rata2']:+.2f} poin",
              f"{s['naif_persen']:+.1f}%")
    c2.metric("Level shift (model)", f"{s['its_level_shift']:+.2f} poin", "p = 0,003",
              delta_color="inverse")
    c3.metric("Perubahan tren", f"{s['its_slope_per_30hari']:+.2f} poin/bulan",
              "efek terkikis")

    gambar("m3_its_counterfactual.png")

    st.markdown(
        f"""
**Cara membaca.** Perbandingan bodoh bilang polusi **naik {s['naif_persen']:.1f}%**
setelah kebijakan. Model bilang sebaliknya: level **turun
{abs(s['its_level_shift']):.2f} poin**. Selisihnya berasal dari pemulihan lalu lintas
pasca-COVID dan musiman yang ditelan mentah-mentah oleh perbandingan naif.

Tapi baca dua koefisien bersamaan: level turun {abs(s['its_level_shift']):.2f},
sementara tren berubah **{s['its_slope_per_30hari']:+.2f} poin per bulan**. Artinya
penurunan itu terkikis — sekitar **{abs(s['its_level_shift']/s['its_slope_per_30hari']):.0f}
bulan** sampai habis. Pola "turun tajam lalu merangkak naik" ini terdokumentasi di
Mexico City (*Hoy No Circula*) dan Beijing, dengan mekanisme adaptasi rumah tangga:
pembelian kendaraan kedua berplat komplementer.
        """
    )
    st.warning("Angka di halaman ini **tidak lolos** uji randomization inference — "
               "lihat tab keempat sebelum mengutipnya.")


# ================================================================ TAB 3
with tab3:
    st.subheader("Empat desain, empat cara gagal")

    desain = pd.DataFrame([
        ["M1", "Triple difference spasial (satelit)", "−2,9% (p=0,006)",
         "Estimasi ada, gagal randomization inference"],
        ["M2", "Triple-diff per jam (stasiun)", "+0,05 (p=0,63)",
         "Alat ukur tidak mampu — data per jam ter-smoothing"],
        ["M3", "Interrupted Time Series", "−3,35 poin (p=0,003)",
         "Estimasi ada, gagal randomization inference"],
        ["M4", "Event study jeda libur", "−26,7 (p<0,001)",
         "Terkonfound mudik — jeda gage selalu berimpit libur"],
    ], columns=["Kode", "Desain", "Koefisien kunci", "Putusan"])
    st.dataframe(desain, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Desain spasial: siapa treated?**")
        gambar("map_cell_classification.png")
        g = D["cells"].group.value_counts()
        st.caption(f"{g.get('treated_13ruas',0)+g.get('treated_both',0)+g.get('treated_new12',0)} "
                   f"sel treated · {g.get('control',0)} kontrol · "
                   f"{g.get('buffer_excluded',0)} buffer dikeluarkan")
    with c2:
        st.markdown("**Kenapa desain per jam gagal**")
        gambar("m2_hourly_profile.png")
        st.caption(
            "Profil rata sepenuhnya. Korelasi jam *t* vs *t+1* = 0,997, dan profil O3 "
            "terbalik secara fotokimia (puncak 03.00). Data 'per jam' yang "
            "dipublikasikan adalah indeks ber-rata-rata bergerak, bukan konsentrasi sesaat."
        )

    st.markdown("---")
    st.markdown("#### Sebelas uji ketahanan")
    m5 = D["m5"].copy()
    m5["p"] = m5.p.round(4)
    st.dataframe(
        m5[["uji", "koef", "se", "p", "catatan"]],
        use_container_width=True, hide_index=True,
        column_config={"uji": st.column_config.TextColumn("Uji", width="large")})
    st.markdown(
        "**Dua lampu kuning.** *R7b*: mengubah jendela waktu membuat estimasi meledak "
        "5× (−14,0) — karena satu-satunya periode gage mati di jendela itu adalah era "
        "COVID. *R4*: intervensi fiktif di September 2021 menghasilkan efek hampir "
        "sebesar efek asli.\n\n"
        "**Satu 'kegagalan' yang bukan kegagalan.** Placebo O3 signifikan positif — "
        "itu *NOx titration*, fenomena kimia atmosfer di mana ozon naik saat NO2 turun. "
        "O3 karenanya tidak sah sebagai placebo, dan tandanya justru konsisten dengan "
        "adanya penurunan NO2 yang nyata."
    )

    with st.expander("Koefisien lengkap M1 (triple difference spasial)"):
        st.dataframe(D["m1"].round(4), use_container_width=True, hide_index=True)


# ================================================================ TAB 4
with tab4:
    st.subheader("Mengapa temuan ini ditarik")
    st.markdown(
        "Dua desain independen menunjukkan penurunan ~3% dan keduanya signifikan "
        "secara konvensional. Uji terakhir membatalkannya: **kalau efek sebesar itu "
        "juga muncul di tanggal dan lokasi acak, maka bukan efek kebijakan."
    )

    m6 = D["m6"]
    c1, c2, c3 = st.columns(3)
    for col, (_, r) in zip((c1, c2, c3), m6.iterrows()):
        lolos = r.ri_p < 0.05
        col.metric(r.uji.replace("RI-A ", "").replace("RI-B ", ""),
                   f"RI p = {r.ri_p:.3f}",
                   "lolos" if lolos else "gagal",
                   delta_color="normal" if lolos else "inverse")

    c1, c2 = st.columns(2)
    with c1:
        gambar("m6_ri_its.png")
        st.caption("37 tanggal intervensi fiktif. Efek asli (merah) berada di "
                   "persentil 27 — sama sekali tidak ekstrem.")
    with c2:
        gambar("m6_ri_did.png")
        st.caption("100 gugus treated palsu. Distribusi ungu (menghormati struktur "
                   "spasial) jauh lebih lebar daripada hijau (acak murni).")

    st.markdown("---")
    st.markdown("#### Temuan metodologis: p-value yang sama, tiga jawaban berbeda")
    st.dataframe(pd.DataFrame([
        ["Cluster-robust SE (konvensional)", "0,006", "signifikan"],
        ["Permutasi acak murni", "0,060", "borderline"],
        ["Permutasi menghormati struktur spasial", "0,500", "tidak informatif"],
    ], columns=["Metode inferensi", "p-value", "Kesimpulan"]),
        use_container_width=True, hide_index=True)
    st.markdown(
        "Untuk koefisien yang **persis sama**. Permutasi acak menghancurkan korelasi "
        "spasial antar sel bertetangga sehingga distribusi null terlalu sempit — "
        "dan inferensi jadi terlalu optimistis. Ini demonstrasi kuantitatif bahwa "
        "**inferensi konvensional pada data spasial beresolusi tinggi bersifat "
        "anti-konservatif.**"
    )

    st.error(
        "**Akar masalahnya struktural, bukan soal spesifikasi model.** Setiap periode "
        "ganjil-genap dimatikan berimpit dengan pandemi (2020–2021) atau libur "
        "panjang/mudik (2023–2026). Tidak pernah ada kondisi *gage mati, kota normal* — "
        "dan tanpa variasi itu, tidak ada desain observasional yang bisa menolong."
    )

    st.markdown(
        "**Apa yang dibutuhkan agar pertanyaan ini terjawab:** konsentrasi µg/m³ "
        "sesaat (bukan rata-rata bergerak), data volume lalu lintas per ruas, atau "
        "variasi kebijakan yang tidak berimpit libur maupun pandemi."
    )


st.markdown("---")
st.caption(
    "Data: Dinas Lingkungan Hidup DKI Jakarta · Sentinel-5P TROPOMI "
    "(EU/ESA/Copernicus via Google Earth Engine) · Open-Meteo. "
    "Metodologi lengkap dan seluruh keputusan yang dikunci sebelum melihat hasil: "
    "`ANALYSIS_PLAN.md`."
)
