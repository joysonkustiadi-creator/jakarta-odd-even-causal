import pandas as pd, glob

for f in sorted(glob.glob("data/raw/mobility/20*_ID_Region_Mobility_Report.csv")):
    df = pd.read_csv(f, low_memory=False)
    jkt = df[df.sub_region_1 == "Jakarta"].copy()
    out = f.replace(".csv", "_jakarta.csv")
    jkt.to_csv(out, index=False)
    print(f"{f}: {len(jkt)} baris Jakarta -> {out}")