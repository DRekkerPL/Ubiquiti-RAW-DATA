import pandas as pd, pathlib
root = pathlib.Path(r"c:\Users\cinex\Documents\Ubiquiti-RAW-DATA")
files = ["ITScope- Ubiquiti 2026.xlsx"]
for f in files:
    try:
        src = root / f
        dest = root / (src.stem + ".csv")
        df = pd.read_excel(src)
        df.to_csv(dest, index=False)
        print('ok', dest)
    except Exception as e:
        print('fail', f, e)
