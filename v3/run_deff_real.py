"""S6: sebaran deff tingkat-uji pada data IDHS NYATA (menentukan apakah heterogenitas relevan).
python run_deff_real.py dataset.csv"""
import sys, itertools, numpy as np, pandas as pd
from sol_v2 import make_D
from sol_v3 import prep, pair_deff, TESTS
VARS = ['perdesaan','p0_daerah_mar2017','sanitasi_klaster_lo','umur_anak_bln','anak_laki','pend_ibu_thn',
        'skor_kekayaan_nonwash','org_per_kamar','punya_ternak','air_layak','cuci_tangan_dasar','olah_air_efektif','T_sanitasi','Y_diare']
d = pd.read_csv(sys.argv[1]).rename(columns={'psu_v021':'psu','strata_v023':'strata'}).dropna(subset=VARS+['bobot','psu','strata'])
D = prep(make_D(d[VARS].to_numpy(float), d.bobot, d.psu, d.strata)); rng = np.random.default_rng(0); rows = []
for i, j in itertools.combinations(range(len(VARS)), 2):
    S = sorted(rng.choice([v for v in range(len(VARS)) if v not in (i, j)], 2, replace=False).tolist())
    rows.append(dict(i=VARS[i], j=VARS[j], deff=pair_deff(D, i, j, S), **{t: f(D, i, j, S) < .05 for t, f in TESTS.items()}))
df = pd.DataFrame(rows); q = df.deff.quantile([.1, .5, .9])
print(f"IDHS nyata: n={D['n']} deff global (rata-rata univariat) {D['deff_global']:.2f} | deff tingkat-uji p10 {q[.1]:.2f} median {q[.5]:.2f} p90 {q[.9]:.2f} maks {df.deff.max():.2f}")
print("proporsi tolak H0 per uji (bukan galat tipe I; data nyata tanpa graf acuan): " + " ".join(f"{t} {df[t].mean():.0%}" for t in TESTS))
