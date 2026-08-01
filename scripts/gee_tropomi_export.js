// =====================================================================
// EKSPOR TROPOMI NO2 — Jakarta, harian per sel grid 3,5 km
//
// Dijalankan di Google Earth Engine Code Editor (code.earthengine.google.com),
// BUKAN di Python lokal. Hasil ekspor masuk ke Google Drive folder
// 'gage_project', lalu diunduh manual ke data/raw/tropomi/.
//
// Dataset : COPERNICUS/S5P/OFFL/L3_NO2
// Band    : tropospheric_NO2_column_number_density (satuan mol/m^2)
// Periode : 2019-01-01 s.d. 2026-07-28 (8 task, satu per tahun)
// Output  : CSV kolom [date, cell_id, lon, lat, mean]
//
// CATATAN PENTING:
//   - Grid didefinisikan SEKALI di luar fungsi agar cell_id konsisten
//     antar tahun. JANGAN mengubah bounding box atau angka 3500 di antara
//     ekspor — panel akan rusak.
//   - Hari tanpa citra (gap orbit) menghasilkan image tanpa band, yang
//     membuat reduceRegions gagal ("Image has no bands"). Ditangani lewat
//     ee.Algorithms.If -> image ber-mask penuh, sehingga barisnya tetap
//     ada dengan mean kosong.
//   - Coverage ~30% (masking awan; kemarau ~48%, musim hujan ~20%).
//     Nilai kosong TIDAK diimputasi di tahap analisis.
//   - Satelit melintas ~13.30 WIB — di luar sesi gage pagi (06-10) dan
//     di awal sesi sore (16-21). Lihat limitasi di ANALYSIS_PLAN.md.
// =====================================================================

var BAND = 'tropospheric_NO2_column_number_density';
var jakarta = ee.Geometry.Rectangle([106.65, -6.40, 107.05, -6.05]);

// Grid tetap ~3,5 km (156 sel) — identik untuk semua tahun
var grid = jakarta.coveringGrid('EPSG:4326', 3500).map(function (f) {
  var c = f.geometry().centroid(1).coordinates();
  return f.set({
    cell_id: f.get('system:index'),
    lon: c.get(0),
    lat: c.get(1)
  });
});

var col = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2')
  .select(BAND)
  .filterBounds(jakarta);

// Rata-rata harian per sel untuk satu rentang tanggal
function buildDaily(startStr, endStr) {
  var start = ee.Date(startStr);
  var nDays = ee.Date(endStr).difference(start, 'day');
  return ee.FeatureCollection(
    ee.List.sequence(0, nDays.subtract(1)).map(function (n) {
      var d = start.advance(n, 'day');
      var sub = col.filterDate(d, d.advance(1, 'day'));
      // Hari tanpa citra -> image ber-mask penuh (mean = kosong)
      var img = ee.Image(ee.Algorithms.If(
        sub.size().gt(0),
        sub.mean(),
        ee.Image.constant(0).updateMask(0).rename(BAND)
      )).rename(BAND);
      return img.reduceRegions({
        collection: grid,
        reducer: ee.Reducer.mean(),
        scale: 3500
      }).map(function (f) {
        return f.set('date', d.format('YYYY-MM-dd'));
      });
    })
  ).flatten();
}

function makeExport(startStr, endStr, label) {
  Export.table.toDrive({
    collection: buildDaily(startStr, endStr),
    description: label,
    folder: 'gage_project',
    fileFormat: 'CSV',
    selectors: ['date', 'cell_id', 'lon', 'lat', 'mean']
  });
}

// ---- 8 task, satu per tahun ----
// Setelah Run, buka tab Tasks di panel kanan dan klik Run pada tiap task.
// Task berjalan di server; browser boleh ditutup setelah semua di-submit.
makeExport('2019-01-01', '2020-01-01', 'tropomi_no2_jakarta_2019');
makeExport('2020-01-01', '2021-01-01', 'tropomi_no2_jakarta_2020');
makeExport('2021-01-01', '2022-01-01', 'tropomi_no2_jakarta_2021');
makeExport('2022-01-01', '2023-01-01', 'tropomi_no2_jakarta_2022');
makeExport('2023-01-01', '2024-01-01', 'tropomi_no2_jakarta_2023');
makeExport('2024-01-01', '2025-01-01', 'tropomi_no2_jakarta_2024');
makeExport('2025-01-01', '2026-01-01', 'tropomi_no2_jakarta_2025');
makeExport('2026-01-01', '2026-07-28', 'tropomi_no2_jakarta_2026');

// ---- Preview visual (opsional, tidak memengaruhi ekspor) ----
Map.centerObject(jakarta, 10);
Map.addLayer(
  col.filterDate('2023-08-01', '2023-08-15').mean(),
  { min: 0, max: 0.0002, palette: ['blue', 'green', 'yellow', 'red'] },
  'NO2 sample'
);