import pandas as pd
import numpy as np

PYTHON = r"C:\Users\cinex\AppData\Local\Programs\Python\Python312\python.exe"
FILE = r"c:\Users\cinex\Documents\Ubiquiti-RAW-DATA\ITScope- Ubiquiti 2026.csv"
OUR_COMPANY = "EET Deutschland"
LATEST = "20260320"

print("Loading data...")
df = pd.read_csv(FILE, low_memory=False)
print(f"  Total rows: {len(df):,}")
print(f"  Date range: {df['extraction_date'].min()} – {df['extraction_date'].max()}")
print(f"  Unique suppliers: {df['supplierName'].nunique()}")
print(f"  Unique SKUs: {df['manufacturerSKU'].nunique()}")

# Use latest snapshot
snap = df[df['extraction_date'] == int(LATEST)].copy()
snap['price'] = pd.to_numeric(snap['price'], errors='coerce').fillna(0)
snap['stock'] = pd.to_numeric(snap['stock'], errors='coerce').fillna(0)
snap_valid = snap[snap['price'] > 0]

eet = snap[snap['supplierName'] == OUR_COMPANY].copy()
eet_skus = set(eet['manufacturerSKU'])
all_skus = set(snap['manufacturerSKU'])

print(f"\n{'='*70}")
print(f"  MARKET SNAPSHOT: {LATEST}")
print(f"{'='*70}")
print(f"  Total SKUs on market:       {len(all_skus):>6}")
print(f"  EET Deutschland SKUs:       {len(eet_skus):>6}  ({len(eet_skus)/len(all_skus)*100:.1f}% coverage)")
print(f"  SKUs missing from EET:      {len(all_skus - eet_skus):>6}")
print(f"  EET total stock (all SKUs): {eet['stock'].sum():>10,.0f} units")
print(f"  Total market stock:         {snap['stock'].sum():>10,.0f} units")
print(f"  EET stock share:            {eet['stock'].sum()/snap['stock'].sum()*100:>9.1f}%")

# ── Per-SKU: market minimum (excl. EET) and EET price ──────────────────────
comp = snap_valid[snap_valid['supplierName'] != OUR_COMPANY]
mkt_min = comp.groupby('manufacturerSKU')['price'].min().rename('mkt_min')
mkt_cnt = comp.groupby('manufacturerSKU')['supplierName'].nunique().rename('competitors')
mkt_stock = comp.groupby('manufacturerSKU')['stock'].sum().rename('mkt_stock')

eet_min = eet.groupby('manufacturerSKU').agg(
    eet_price=('price','min'),
    eet_stock=('stock','sum')
)

compare = eet_min.join(mkt_min).join(mkt_cnt).join(mkt_stock).dropna(subset=['mkt_min'])
compare = compare[compare['mkt_min'] > 0]
compare['gap_pct'] = (compare['eet_price'] - compare['mkt_min']) / compare['mkt_min'] * 100

n_cheaper  = (compare['gap_pct'] < -1).sum()
n_parity   = (compare['gap_pct'].between(-1, 1)).sum()
n_costlier = (compare['gap_pct'] > 1).sum()
avg_gap    = compare['gap_pct'].mean()
median_gap = compare['gap_pct'].median()

print(f"\n{'='*70}")
print(f"  EET PRICE POSITION vs CHEAPEST COMPETITOR  (n={len(compare)} SKUs with data)")
print(f"{'='*70}")
print(f"  EET is cheapest  (>1% below mkt min):   {n_cheaper:>5} SKUs  ({n_cheaper/len(compare)*100:.1f}%)")
print(f"  EET at parity    (within ±1%):          {n_parity:>5} SKUs  ({n_parity/len(compare)*100:.1f}%)")
print(f"  EET more costly  (>1% above mkt min):   {n_costlier:>5} SKUs  ({n_costlier/len(compare)*100:.1f}%)")
print(f"\n  Average price gap vs cheapest:  {avg_gap:+.2f}%")
print(f"  Median  price gap vs cheapest:  {median_gap:+.2f}%")

# Distribution buckets
bins   = [-np.inf,-50,-20,-10,-5,-1,1,5,10,20,50,100,np.inf]
labels = ['<-50%','-50 to -20%','-20 to -10%','-10 to -5%','-5 to -1%',
          '±1% (parity)','1–5% above','5–10% above','10–20% above',
          '20–50% above','50–100% above','>100% above']
compare['bucket'] = pd.cut(compare['gap_pct'], bins=bins, labels=labels)

print(f"\n  Price gap distribution:")
for lbl, cnt in compare['bucket'].value_counts(sort=False).items():
    bar = '#' * (cnt // 3)
    print(f"    {lbl:<22} {cnt:>4}  {bar}")

# ── TOP 20 most expensive vs market ────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  TOP 20 SKUs WHERE EET IS MOST OVERPRICED (vs cheapest competitor)")
print(f"{'='*70}")
print(f"  {'SKU':<24} {'EET €':>9} {'Mkt Min €':>9} {'Gap':>9} {'EET Stock':>10} {'Competitors':>12}")
print(f"  {'-'*68}")
top_exp = compare.nlargest(20, 'gap_pct')
for sku, row in top_exp.iterrows():
    print(f"  {sku:<24} {row['eet_price']:>9.2f} {row['mkt_min']:>9.2f} {row['gap_pct']:>+8.1f}% {row['eet_stock']:>10.0f} {row['competitors']:>12.0f}")

# ── TOP 15 competitors cheaper than EET (shared SKU count) ─────────────────
print(f"\n{'='*70}")
print(f"  COMPETITOR THREAT MATRIX  (on shared SKUs, latest snapshot)")
print(f"{'='*70}")
print(f"  {'Competitor':<36} {'Shared':>7} {'Cheaper':>8} {'Avg Gap':>9} {'Comp Stock':>11} {'EET Stock':>10}")
print(f"  {'':36} {'SKUs':>7} {'than EET':>8} {'vs EET':>9}")
print(f"  {'-'*85}")

results = []
for supplier, grp in comp.groupby('supplierName'):
    shared = compare.index.intersection(grp.set_index('manufacturerSKU').index)
    if len(shared) < 20:
        continue
    sub = grp[grp['manufacturerSKU'].isin(shared)].groupby('manufacturerSKU')['price'].min()
    eet_sub = compare.loc[shared, 'eet_price']
    gaps = (sub - eet_sub) / eet_sub * 100  # neg = comp cheaper
    cheaper_cnt = (gaps < -1).sum()
    avg_gap_comp = gaps.mean()
    comp_stock = grp[grp['manufacturerSKU'].isin(shared)]['stock'].sum()
    eet_stock_shared = compare.loc[shared, 'eet_stock'].sum()
    results.append({
        'supplier': supplier,
        'shared': len(shared),
        'cheaper': cheaper_cnt,
        'avg_gap': avg_gap_comp,
        'comp_stock': comp_stock,
        'eet_stock': eet_stock_shared
    })

res_df = pd.DataFrame(results).sort_values('cheaper', ascending=False)
for _, r in res_df.head(20).iterrows():
    print(f"  {r['supplier']:<36} {r['shared']:>7.0f} {r['cheaper']:>8.0f} {r['avg_gap']:>+8.1f}% {r['comp_stock']:>11,.0f} {r['eet_stock']:>10,.0f}")

# ── Supplier SKU & stock overview ──────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  MARKET OVERVIEW: SKU COVERAGE & STOCK (top 20 suppliers)")
print(f"{'='*70}")
print(f"  {'Supplier':<36} {'SKUs':>7} {'Total Stock':>13} {'Stock Rank':>11}")
print(f"  {'-'*70}")
sup_agg = snap.groupby('supplierName').agg(
    skus=('manufacturerSKU','nunique'),
    total_stock=('stock','sum')
).sort_values('total_stock', ascending=False).reset_index()
sup_agg['rank'] = range(1, len(sup_agg)+1)
for _, r in sup_agg.head(20).iterrows():
    marker = ' <<< EET' if r['supplierName'] == OUR_COMPANY else ''
    print(f"  {(r['supplierName']+marker):<36} {r['skus']:>7} {r['total_stock']:>13,.0f}  #{r['rank']}")

# ── SKUs missing from EET with high market demand ──────────────────────────
missing = all_skus - eet_skus
miss_df = snap[snap['manufacturerSKU'].isin(missing)].groupby('manufacturerSKU').agg(
    competitors=('supplierName','nunique'),
    market_stock=('stock','sum'),
    min_price=('price', lambda x: x[x>0].min() if (x>0).any() else 0)
).sort_values('competitors', ascending=False)

print(f"\n{'='*70}")
print(f"  TOP 30 SKUs MISSING FROM EET (by # competitors listing them)")
print(f"{'='*70}")
print(f"  {'SKU':<26} {'Competitors':>12} {'Mkt Stock':>11} {'Min Price €':>12}")
print(f"  {'-'*65}")
for sku, row in miss_df.head(30).iterrows():
    print(f"  {sku:<26} {row['competitors']:>12.0f} {row['market_stock']:>11,.0f} {row['min_price']:>12.2f}")

# ── Price trend: EET avg gap per week ──────────────────────────────────────
print(f"\n{'='*70}")
print(f"  EET PRICE COMPETITIVENESS TREND (avg gap % vs cheapest, weekly samples)")
print(f"{'='*70}")
print(f"  {'Date':<12} {'EET SKUs':>9} {'Avg Gap%':>10} {'Overpriced':>11} {'Underpriced':>12}")
print(f"  {'-'*57}")

weekly_dates = [20260105,20260112,20260119,20260126,20260202,20260209,
                20260216,20260223,20260302,20260309,20260316,20260320]

for d in weekly_dates:
    s = df[df['extraction_date'] == d].copy()
    s['price'] = pd.to_numeric(s['price'], errors='coerce').fillna(0)
    eet_s = s[s['supplierName'] == OUR_COMPANY]
    comp_s = s[(s['supplierName'] != OUR_COMPANY) & (s['price'] > 0)]
    mkt_s = comp_s.groupby('manufacturerSKU')['price'].min()
    eet_s2 = eet_s[eet_s['price'] > 0].groupby('manufacturerSKU')['price'].min()
    merged = pd.DataFrame({'eet': eet_s2, 'mkt': mkt_s}).dropna()
    merged = merged[merged['mkt'] > 0]
    merged['gap'] = (merged['eet'] - merged['mkt']) / merged['mkt'] * 100
    avg = merged['gap'].mean()
    over = (merged['gap'] > 1).sum()
    under = (merged['gap'] < -1).sum()
    print(f"  {str(d):<12} {len(eet_s2):>9} {avg:>+9.2f}% {over:>11} {under:>12}")

print(f"\n{'='*70}")
print("  SUMMARY & KEY FINDINGS")
print(f"{'='*70}")
print(f"""
  1. SKU COVERAGE: EET lists {len(eet_skus)} of {len(all_skus)} market SKUs = {len(eet_skus)/len(all_skus)*100:.1f}%
     → {len(all_skus - eet_skus)} SKUs not listed — opportunity to expand portfolio

  2. STOCK LEADERSHIP: EET holds {eet['stock'].sum():,.0f} units total
     → #1 in stock depth — significant availability advantage

  3. PRICE POSITION: avg +{avg_gap:.1f}% above cheapest competitor (median +{median_gap:.1f}%)
     → {n_costlier} SKUs priced >1% above cheapest ({n_costlier/len(compare)*100:.0f}% of portfolio)
     → {n_cheaper} SKUs where EET is actually cheapest
     → Core issue: accessories/niche SKUs show 100-1300% overpricing

  4. SHARPEST THREATS (most SKUs cheaper than EET):
     → ALLNET Deutschland:  {res_df[res_df.supplier=='ALLNET Deutschland']['cheaper'].values[0]:.0f} SKUs cheaper
     → TRIOTRONIK:          {res_df[res_df.supplier=='TRIOTRONIK']['cheaper'].values[0]:.0f} SKUs cheaper
     → Siewert & Kau:       {res_df[res_df.supplier=='Siewert & Kau']['cheaper'].values[0]:.0f} SKUs cheaper
     → Alldis Computer:     {res_df[res_df.supplier=='Alldis Computer']['cheaper'].values[0]:.0f} SKUs cheaper

  5. LARGEST SKU COMPETITOR: Octo IT ({sup_agg[sup_agg.supplierName=='Octo IT']['skus'].values[0]} SKUs) but avg +80% above EET → no price threat
""")
