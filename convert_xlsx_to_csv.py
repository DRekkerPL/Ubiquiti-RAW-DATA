import pandas as pd, pathlib
root = pathlib.Path(r"c:\Users\cinex\Documents\Ubiquiti-RAW-DATA")
files = ["Current Margins Ubiquiti - Tracker.xlsx", "Current Sales Germany.xlsx", "ITScope- Ubiquiti 2026.xlsx"]
for f in files:
    src = root / f
    dest = root / (src.stem + ".csv")
    df = pd.read_excel(src)
    df.to_csv(dest, index=False)
    print(dest)
