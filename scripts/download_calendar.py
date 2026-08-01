import holidays
import pandas as pd
from pathlib import Path

OUT = Path("data/raw/calendar")
OUT.mkdir(parents=True, exist_ok=True)

id_hol = holidays.Indonesia(years=range(2019, 2027))
cal = pd.DataFrame(
    [(d, n) for d, n in sorted(id_hol.items())],
    columns=["date", "holiday_name"],
)
path = OUT / "holidays_id.csv"
cal.to_csv(path, index=False)

print(f"OK — {len(cal)} hari libur -> {path}")
print("\nCek sampel (harus ada Idul Fitri, Nyepi, Natal, dll):")
print(cal[cal.holiday_name.str.contains("Idul Fitri|Nyepi", case=False)]
      .to_string(index=False))