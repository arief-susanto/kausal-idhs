"""S6+S7+S9: dampak hilir tiap uji.  python run_downstream.py [reps] [p] [design.csv]"""
import sys, numpy as np, pandas as pd
from sol_v3 import design_idhs, simulate_v3, downstream
reps = int(sys.argv[1]) if len(sys.argv) > 1 else 50; p = int(sys.argv[2]) if len(sys.argv) > 2 else 15
des = design_idhs(sys.argv[3] if len(sys.argv) > 3 else None); rows = []
for sc, icc in {'heterogen': (0.1, 0.8), 'homogen': 0.45}.items():
    for r in range(reps):
        D, G, tiers, T, Y, true, _ = simulate_v3(r, des, p=p, icc=icc, beta_ty=-0.3)
        for x in downstream(D, G, tiers, T, Y, true, seed=r): rows.append(dict(skenario=sc, rep=r, **x))
df = pd.DataFrame(rows); df.to_csv(f'hasil_downstream_p{p}.csv', index=False)
tab = df.groupby(['skenario', 'uji']).agg(SHD=('SHD', 'mean'), presisi=('presisi', 'mean'), recall=('recall', 'mean'),
      FDR=('FDR', 'mean'), adj_valid=('adj_valid', 'mean'), RMSE=('err', lambda e: np.sqrt((e**2).mean())),
      cakupan=('cover', 'mean'), cakupan_union=('cover_union', 'mean'), detik=('detik', 'mean'), MB=('MB', 'mean'))
s = f"DOWNSTREAM p={p} reps={reps}\n" + tab.round(3).to_string(); open(f'RINGKASAN_downstream_p{p}.txt', 'w').write(s); print(s)
