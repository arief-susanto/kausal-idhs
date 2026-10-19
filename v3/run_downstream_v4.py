"""S12+S13+S14 (+S15): dampak hilir, himpunan cadangan, α sadar-query, bias himpunan.
    python run_downstream_v4.py [reps=100] [p=15] [design.csv] [n_proses=7]
Keluaran: hasil_v4_p{p}.csv, RINGKASAN_v4_p{p}.txt. Uji hipotesis sesuai PRAREGISTRASI_S12_S15.md."""
import sys, numpy as np, pandas as pd
from multiprocessing import Pool
from scipy import stats
from sol_v3 import design_idhs, simulate_v3
from sol_v4 import downstream_v4

A = sys.argv; reps = int(A[1]) if len(A) > 1 else 100; p = int(A[2]) if len(A) > 2 else 15
path = A[3] if len(A) > 3 and A[3] != '-' else None; nproc = int(A[4]) if len(A) > 4 else 7
SCEN = {'heterogen': (0.1, 0.8), 'homogen': 0.45}

def job(arg):
    sc, r = arg; D, G, tiers, T, Y, true, _ = simulate_v3(r, design_idhs(path), p=p, icc=SCEN[sc], beta_ty=-0.3)
    return [dict(skenario=sc, rep=r, **x) for x in downstream_v4(D, G, tiers, T, Y, true, seed=r)]

def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); m = len(ps); run = 0
    for rank, i in enumerate(o): run = max(run, (m - rank) * ps[i]); adj[i] = min(run, 1)
    return adj

def boot_lo(d, B=5000, seed=0):
    """Batas bawah bootstrap persentil satu sisi 95% untuk rata-rata d."""
    rng = np.random.default_rng(seed); d = np.asarray(d, float)
    return float(np.quantile(rng.choice(d, (B, len(d))).mean(1), .05))

def wil(d, alt):
    d = np.asarray(d, float); return 1.0 if np.all(d == 0) else stats.wilcoxon(d, alternative=alt, zero_method='zsplit').pvalue

def hypotheses(df):
    L = []
    for sc, g in df.groupby('skenario'):
        W = {c: g.pivot(index='rep', columns='uji', values=c) for c in ('adj_valid', 'adj_valid_S12', 'FDR', 'bias_set')}
        base = ['naif', 'kish', 'deff_global', 'sandwich_CR1', 'desain_usulan']
        ps = [wil(W['adj_valid_S12'][u] - W['adj_valid'][u], 'greater') for u in base]; ph = holm(ps)
        L.append(f"[{sc}] H12a validitas S12 > utama (Wilcoxon satu sisi, Holm): "
                 + ", ".join(f"{u} p={h:.3g}" for u, h in zip(base, ph)))
        cv = g[g.uji == 'desain_usulan'].cover_S12.mean()
        L.append(f"[{sc}] H12b cakupan S12 desain_usulan = {cv:.1%} (kriteria ≥ 92%) -> {'DITERIMA' if cv >= .92 else 'DITOLAK'}")
        for a in (10, 20, 30):
            s13 = f'desain_S13_a{a}'
            lo_f = boot_lo(-(W['FDR'][s13] - W['FDR']['desain_usulan']) + .02)   # FDR_S13 - FDR_desain ≤ 0,02
            lo_v = boot_lo(W['adj_valid'][s13] - W['adj_valid']['naif'] + .05)  # valid_S13 - valid_naif ≥ -0,05
            ok = lo_f > 0 and lo_v > 0; tag = 'H13 (UTAMA)' if a == 20 else 'H13 (sensitivitas)'
            L.append(f"[{sc}] {tag} α_q=0,{a}: ΔFDR vs desain={(W['FDR'][s13]-W['FDR']['desain_usulan']).mean():+.3f} "
                     f"[NI lo={lo_f:+.3f}], Δvalid vs naif={(W['adj_valid'][s13]-W['adj_valid']['naif']).mean():+.3f} "
                     f"[NI lo={lo_v:+.3f}] -> {'DITERIMA' if ok else 'DITOLAK'}")
    return L

if __name__ == '__main__':
    args = [(sc, r) for sc in SCEN for r in range(reps)]
    with Pool(nproc) as pool:
        rows = [x for res in pool.imap_unordered(job, args) for x in res]
    df = pd.DataFrame(rows).sort_values(['skenario', 'rep', 'uji']); df.to_csv(f'hasil_v4_p{p}.csv', index=False)
    agg = dict(SHD=('SHD', 'mean'), FDR=('FDR', 'mean'), recall=('recall', 'mean'), rec_TY=('recall_TY', 'mean'),
               FDR_TY=('FDR_TY', 'mean'), valid=('adj_valid', 'mean'), valid_S12=('adj_valid_S12', 'mean'),
               RMSE=('err', lambda e: np.sqrt((e**2).mean())), RMSE_S12=('err_S12', lambda e: np.sqrt((e**2).mean())),
               cak=('cover', 'mean'), cak_S12=('cover_S12', 'mean'), absbias=('bias_set', lambda b: b.abs().mean()),
               absbias_S12=('bias_set_S12', lambda b: b.abs().mean()), material=('material', 'mean'),
               material_S12=('material_S12', 'mean'), k=('k_set', 'mean'), k_S12=('k_set_S12', 'mean'), detik=('detik', 'mean'))
    tab = df.groupby(['skenario', 'uji']).agg(**agg)
    inv = df[df.adj_valid < 1].groupby(['skenario', 'uji']).material.mean().rename('material|tidak_sah')
    s = (f"DOWNSTREAM v4 p={p} reps={reps}\n" + tab.round(3).to_string() + "\n\nS14 proporsi material di antara himpunan tidak sah:\n"
         + inv.round(3).to_string() + "\n\nUJI HIPOTESIS (PRAREGISTRASI_S12_S15.md)\n" + "\n".join(hypotheses(df)))
    open(f'RINGKASAN_v4_p{p}.txt', 'w', encoding='utf-8').write(s); print(s)
