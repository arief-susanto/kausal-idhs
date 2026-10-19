"""Jalankan SOL v2 pada data nyata: python run_idhs.py dataset.csv [analisis]
Dataset = keluaran menu Persiapan Data (kolom bobot/psu/strata atau bobot/psu_v021/strata_v023)."""
import sys, numpy as np, pandas as pd
from sol_v2 import make_D, query_effect
# Tier: 0 konteks, 1 demografi, 2 ekonomi, 3 WASH/akses (treatment), 4 outcome. Ubah di sini saja.
ANALISIS = {
 'sanitasi_diare': dict(T='T_sanitasi', Y='Y_diare', filter=None, tiers={
   'perdesaan':0,'p0_daerah_mar2017':0,'sanitasi_klaster_lo':0,'cuci_tangan_klaster_lo':0,
   'umur_anak_bln':1,'anak_laki':1,'pend_ibu_thn':1,
   'skor_kekayaan_nonwash':2,'org_per_kamar':2,'punya_ternak':2,
   'air_layak':3,'cuci_tangan_dasar':3,'olah_air_efektif':3,'T_sanitasi':3,'Y_diare':4}),
 'pbi_diare': dict(T='T_pbi', Y='Y_diare', filter=None, tiers={
   'perdesaan':0,'p0_daerah_mar2017':0,'pbi_pct_prov':0,'umur_anak_bln':1,'anak_laki':1,'pend_ibu_thn':1,
   'kk_perempuan':1,'jml_art':1,'skor_kekayaan_nonwash':2,'ibu_bekerja':2,'hambatan_biaya':3,
   'air_layak':3,'T_sanitasi':3,'T_pbi':3,'Y_diare':4}),
}
path = sys.argv[1]; names = sys.argv[2:] or list(ANALISIS)
raw = pd.read_csv(path).rename(columns={'psu_v021':'psu','strata_v023':'strata'})
for nm in names:
    a = ANALISIS[nm]; cols = list(a['tiers']); T, Y = cols.index(a['T']), cols.index(a['Y'])
    d = (raw.query(a['filter']) if a['filter'] else raw).dropna(subset=cols + ['bobot','psu','strata'])
    D = make_D(d[cols].to_numpy(float), d.bobot, d.psu, d.strata)
    r = query_effect(D, T, Y, [a['tiers'][c] for c in cols], alpha=0.05, K=2, design=True)
    und = [(cols[i], cols[j]) for i, j in r['U']]
    print(f"{nm}: n={D['n']} sisi={r['G'].number_of_edges()}+{len(und)} tak-berarah | "
          f"RD {r['rd']:+.4f} [{r['lo']:+.4f}; {r['hi']:+.4f}] | kandidat himpunan induk={r['n_set']} "
          f"rentang {r['rd_set'][0]:+.4f}..{r['rd_set'][1]:+.4f} | induk T: {[cols[i] for i in r['G'].predecessors(T)]}")
