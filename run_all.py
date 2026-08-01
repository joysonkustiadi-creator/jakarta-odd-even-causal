"""
Jalankan seluruh pipeline secara berurutan.

    python run_all.py                # analisis saja (default, ~5-25 menit)
    python run_all.py --with-download # termasuk unduh cuaca & scraping (+45 menit)
    python run_all.py --keep-going    # lanjut walau ada script gagal

Script pengumpul data dilewati secara default karena lambat dan sudah
menghasilkan file di data/raw/. Ekspor TROPOMI (gee_tropomi_export.js)
tidak dapat dijalankan dari sini — harus lewat code.earthengine.google.com.
"""
import subprocess, sys, time
from pathlib import Path

DOWNLOAD = [
    "download_weather.py",      # ~2 menit
    "download_calendar.py",     # ~10 detik
    "scrape_rendahemisi.py",    # ~45 menit (punya mekanisme resume)
    "filter_mobility.py",       # butuh file Google Mobility
]

PIPELINE = [
    # --- bangun tabel analisis (urutan wajib) ---
    "build_ispu_panel.py",
    "build_master_panel.py",
    "classify_cells.py",
    # --- analisis (boleh diacak, tapi ini urutan naratifnya) ---
    "did_first.py",
    "hourly_triplediff.py",
    "its_main.py",
    "event_study_switches.py",
    "robustness.py",
    "randomization_inference.py",
]

def run(nama):
    path = Path("scripts") / nama
    if not path.exists():
        print(f"  ! {nama} tidak ditemukan — dilewati")
        return None
    print(f"\n{'='*70}\n>>> {nama}\n{'='*70}")
    t0 = time.time()
    hasil = subprocess.run([sys.executable, str(path)])
    dt = time.time() - t0
    status = "OK" if hasil.returncode == 0 else f"GAGAL (kode {hasil.returncode})"
    print(f"--- {nama}: {status} dalam {dt:.0f}s")
    return hasil.returncode == 0

if __name__ == "__main__":
    args = sys.argv[1:]
    daftar = (DOWNLOAD if "--with-download" in args else []) + PIPELINE
    keep_going = "--keep-going" in args

    print(f"Akan menjalankan {len(daftar)} script.\n")
    ringkas, t_awal = [], time.time()

    for nama in daftar:
        ok = run(nama)
        ringkas.append((nama, ok))
        if ok is False and not keep_going:
            print("\nBERHENTI: script gagal. Perbaiki dulu, "
                  "atau jalankan ulang dengan --keep-going.")
            break

    print(f"\n{'='*70}\nRINGKASAN ({time.time()-t_awal:.0f}s total)\n{'='*70}")
    for nama, ok in ringkas:
        tanda = "OK  " if ok else ("SKIP" if ok is None else "GAGAL")
        print(f"  [{tanda}] {nama}")