"""S8 (INTI): kalibrasi 5 uji CI menurut heterogenitas deff.   python run_s8.py [reps] [design.csv]
Skenario: ICC heterogen vs homogen (rata-rata sama). Keluaran: RINGKASAN_S8.txt (≤ 15 baris)."""
import sys, numpy as np, pandas as pd
from sol_v3 import design_idhs, simulate_v3, calibration, TESTS
from statsmodels.stats.proportion import proportion_confint as wilson
reps = int(sys.argv[1]) if len(sys.argv) > 1 else 100; des = design_idhs(sys.argv[2] if len(sys.argv) > 2 else None)
SCEN = {'heterogen': (0.1, 0.8), 'homogen': 0.45}  # (0.1,0.8) dikalibrasi ke deff tingkat-uji IDHS nyata (median 2,39)
rows = []
for sc, icc in SCEN.items():
    for r in range(reps):
        D, G, *_ = simulate_v3(r, des, p=15, icc=icc, beta_ty=-0.3)
        for x in calibration(D, G, seed=r): rows.append(dict(skenario=sc, rep=r, **x))
df = pd.DataFrame(rows); df.to_csv('hasil_S8.csv', index=False)
df['bin_deff'] = pd.cut(df.deff, [0, 1.5, 3, np.inf], labels=['<1,5', '1,5–3', '>3'])
L = []
for sc, g in df.groupby('skenario'):
    h0 = g[g.indep]; h1 = g[~g.indep]
    L.append(f"[{sc}] n H0={len(h0)} H1={len(h1)} | deff median {g.deff.median():.2f}")
    for t in TESTS:
        k = int(h0[t].sum()); lo, hi = wilson(k, len(h0), method='wilson')
        cnt = h0.groupby('bin_deff', observed=True)[t].agg(['mean', 'size']); per = cnt['mean'][cnt['size'] >= 30]  # bin < 30 pernyataan diabaikan
        worst = (per - .05).abs().max() if len(per) else float('nan')
        L.append(f"  {t:13s} tipeI {k/len(h0):.1%} [{lo:.1%}-{hi:.1%}] per-bin "
                 + " ".join(f"{b}:{v:.1%}" for b, v in per.items()) + f" | maks|dev| {worst:.1%} | daya {h1[t].mean():.1%}")
    same = (h0['sandwich_CR1'] == h0['desain_usulan']).mean(); L.append(f"  keputusan identik usulan vs sandwich_CR1 pada H0: {same:.1%}")
open('RINGKASAN_S8.txt', 'w').write("\n".join(L)); print("\n".join(L))
