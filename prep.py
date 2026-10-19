"""MENU 1: PERSIAPAN DATA. IDBR71 + IDHR71 + konteks provinsi -> cache/analisis.pkl"""
import zipfile
import numpy as np
import pandas as pd
import config as C

BR_COLS = ['caseid', 'bidx', 'v001', 'v002', 'v005', 'v021', 'v023', 'v024', 'v025', 'v008', 'b3', 'b0',
           'b4', 'b5', 'b6', 'b7', 'bord', 'v012', 'v106', 'v133', 'v701', 'v136', 'v151', 'v714',
           'v467c', 'v467d', 'v481', 'v481c', 'v481e', 'v113', 'v116', 'm14', 'm15', 'm17',
           'm3a', 'm3b', 'm3c', 'm3d', 'm3e', 'h11', 'h31', 'h31b', 'h31c']
HR_COLS = ['hv001', 'hv002', 'hv005', 'hv009', 'hv216', 'hv230a', 'hv230b', 'hv232', 'hv237', 'hv237a',
           'hv237b', 'hv237d', 'hv242', 'hv244', 'hv246', 'hv247', 'sh112b', 'hv206', 'hv207', 'hv208',
           'hv209', 'hv210', 'hv211', 'hv212', 'hv221', 'sh121g', 'sh121h', 'sh121i', 'hv213', 'hv214',
           'hv215', 'hv226']


def _dta(kode, cols):
    """Ekstrak .DTA dari zip sekali saja, lalu baca kolom yang perlu."""
    C.CACHE.mkdir(exist_ok=True)
    dta = C.CACHE / f"{kode}FL.DTA"
    if not dta.exists():
        with zipfile.ZipFile(C.RAW / f"{kode}DT.zip") as z:
            z.extract(f"{kode}FL.DTA", C.CACHE)
    return pd.read_stata(dta, convert_categoricals=False, columns=cols)


b01 = lambda x: x.where(x.isin([0, 1]))


def _bin(cond, valid):
    return cond.astype(float).where(valid)


def _loo(df, key, var):
    """Rata-rata klaster tanpa unit itu sendiri (leave-one-out)."""
    g = df.groupby(key)[var]
    s, n, own = g.transform('sum'), g.transform('count'), df[var].notna().astype(int)
    return ((s - df[var].fillna(0)) / (n - own)).where(n - own > 0)


def wealth_nonwash(h):
    """PCA aset tanpa air, toilet, ternak. Kuintil populasi (bobot RT x ART) seperti DHS."""
    I = pd.DataFrame({k: b01(h[v]) for k, v in dict(
        listrik='hv206', radio='hv207', tv='hv208', kulkas='hv209', sepeda='hv210', motor='hv211',
        mobil='hv212', telepon='hv221', kipas='sh121g', mesin_cuci='sh121h', ac='sh121i',
        bank='hv247', tanah='hv244', dapur='hv242').items()})
    I['lantai'] = h.hv213.isin(range(31, 37)).astype(float)
    I['dinding'] = h.hv214.isin([32, 34, 35, 36, 37, 38]).astype(float)
    I['atap'] = h.hv215.isin(range(31, 37)).astype(float)
    I['bbm_bersih'] = h.hv226.isin([1, 2, 3, 4]).astype(float)
    I['org_kamar'] = (h.hv009 / h.hv216.replace(0, np.nan)).clip(upper=15)
    I = I.fillna(I.mean())
    Z = (I - I.mean()) / I.std(ddof=0)
    val, vec = np.linalg.eigh(np.cov(Z.T))
    v = vec[:, -1] * np.sign(vec[list(I.columns).index('tv'), -1])
    skor = pd.Series(Z.values @ v, index=h.index)
    s = skor.sort_values(); pw = (h.hv005 * h.hv009).loc[s.index]
    q = np.minimum(np.ceil(pw.cumsum() / pw.sum() * 5), 5).astype(int)
    return skor, q.reindex(h.index), val[-1] / val.sum()


def run():
    br, hr = _dta("IDBR71", BR_COLS), _dta("IDHR71", HR_COLS)
    d = br[(br.v008 - br.b3) < 60].copy()                     # kelahiran 5 tahun terakhir
    o = pd.DataFrame({'caseid': d.caseid, 'bidx': d.bidx, 'klaster': d.v001, 'rt': d.v002,
                      'bobot': d.v005 / 1e6, 'psu': d.v021, 'strata': d.v023,
                      'kode_prov_v024': d.v024, 'perdesaan': (d.v025 == 2).astype(int),
                      'umur_anak_bln': d.v008 - d.b3})
    # --- treatment
    o['T_pbi'] = b01(d.v481c)            # label DHS tertukar; divalidasi dg s309c
    o['jkn_nonpbi'] = b01(d.v481e)
    san_ok = [11, 12, 13, 15, 17, 21, 22, 41]
    valid_san = d.v116.notna() & ~d.v116.isin([96, 97])
    o['T_sanitasi'] = _bin(d.v116.isin(san_ok) & (d.v116 != 17), valid_san)
    o['T_fasilitas'] = _bin(d.m15.between(21, 37), d.m15.notna())
    o['T_fasilitas_ketat'] = _bin(d.m15.isin([21, 22, 23, 24, 26, 31, 32, 33]), d.m15.notna())
    # --- outcome
    hidup = d.b5 == 1
    o['Y_diare'] = np.where(d.h11.isin([1, 2]), 1.0, np.where(d.h11 == 0, 0.0, np.nan))
    ari = d.h31.isin([1, 2]) & (d.h31b == 1) & d.h31c.isin([1, 3])
    o['Y_ispa'] = _bin(ari, d.h31.notna() & ~d.h31.isin([8, 9]))
    o.loc[~hidup, ['Y_diare', 'Y_ispa']] = np.nan
    o['Y_mati_neonatal'] = _bin((d.b5 == 0) & d.b6.between(100, 130), (d.v008 - d.b3) >= 1)
    o['Y_mati_bayi'] = _bin((d.b5 == 0) & (d.b7 < 12), (d.v008 - d.b3) >= 12)
    # --- mediator & kovariat
    o['M_anc4'] = np.where(d.m14.between(4, 90), 1.0, np.where(d.m14.between(0, 3), 0.0, np.nan))
    o['M_nakes'] = _bin((d[['m3a', 'm3b', 'm3c', 'm3d', 'm3e']] == 1).any(axis=1), d.m3a.notna())
    o['M_sesar'] = b01(d.m17)
    air_ok = [10, 11, 12, 13, 14, 20, 21, 31, 41, 51, 61, 62, 71, 72]
    o['air_layak'] = _bin(d.v113.isin(air_ok), d.v113.notna() & ~d.v113.isin([96, 97]))
    o['umur_ibu'], o['pend_ibu_thn'] = d.v012, d.v133.where(d.v133 < 30)
    o['pend_suami_kat'] = d.v701.where(d.v701.isin([0, 1, 2, 3]))
    o['ind_pend_ibu_level'] = d.v106.where(d.v106.isin([0, 1, 2, 3]))      # indikator MLC-DAG
    o['anak_laki'], o['kembar'], o['urutan_lahir'] = (d.b4 == 1).astype(int), (d.b0 > 0).astype(int), d.bord
    o['jml_art'], o['kk_perempuan'], o['ibu_bekerja'] = d.v136, (d.v151 == 2).astype(int), b01(d.v714)
    o['hambatan_biaya'] = _bin(d.v467c == 1, d.v467c.isin([0, 1, 2]))
    o['hambatan_jarak'] = _bin(d.v467d == 1, d.v467d.isin([0, 1, 2]))
    # --- rumah tangga (HR)
    h = hr.copy()
    h['skor_kekayaan_nonwash'], h['kuintil_kekayaan_nonwash'], ve = wealth_nonwash(h)
    h['cuci_tangan_dasar'] = np.where(h.hv230a.isin([1, 2]), ((h.hv230b == 1) & (h.hv232 == 1)).astype(float),
                                      np.where(h.hv230a == 3, 0.0, np.nan))
    h['olah_air_efektif'] = np.where(h.hv237 == 1, ((h.hv237a == 1) | (h.hv237b == 1) | (h.hv237d == 1)).astype(float),
                                     np.where(h.hv237 == 0, 0.0, np.nan))
    h['punya_ternak'], h['org_per_kamar'] = b01(h.hv246), h.hv009 / h.hv216.replace(0, np.nan)
    h['jarak_sumur_septik_m'] = h.sh112b.where(h.sh112b < 98)
    # indikator aset per item untuk konstruk ekonomi MLC-DAG (tanpa air, toilet, ternak)
    for k, v in dict(listrik='hv206', tv='hv208', kulkas='hv209', motor='hv211', mobil='hv212', bank='hv247').items():
        h[f'ind_{k}'] = b01(h[v])
    for k, v, ok in [('lantai', 'hv213', range(31, 37)), ('dinding', 'hv214', [32, 34, 35, 36, 37, 38]),
                     ('atap', 'hv215', range(31, 37))]:
        h[f'ind_{k}'] = h[v].isin(ok).astype(float).where(h[v].notna() & (h[v] < 99))
    hk = ['skor_kekayaan_nonwash', 'kuintil_kekayaan_nonwash', 'cuci_tangan_dasar', 'olah_air_efektif',
          'punya_ternak', 'org_per_kamar', 'jarak_sumur_septik_m'] + [c for c in h if c.startswith('ind_')]
    o = o.merge(h[['hv001', 'hv002'] + hk], left_on=['klaster', 'rt'], right_on=['hv001', 'hv002'],
                how='left').drop(columns=['hv001', 'hv002'])
    # --- agregat klaster leave-one-out
    o['fasilitas_klaster_lo'] = _loo(o, 'klaster', 'T_fasilitas')
    rt = o.drop_duplicates(['klaster', 'rt'])[['klaster', 'rt', 'T_sanitasi', 'cuci_tangan_dasar']].copy()
    rt['sanitasi_klaster_lo'] = _loo(rt, 'klaster', 'T_sanitasi')
    rt['cuci_tangan_klaster_lo'] = _loo(rt, 'klaster', 'cuci_tangan_dasar')
    o = o.merge(rt[['klaster', 'rt', 'sanitasi_klaster_lo', 'cuci_tangan_klaster_lo']], on=['klaster', 'rt'])
    ib = o.drop_duplicates('caseid')[['caseid', 'klaster', 'hambatan_jarak']].copy()
    ib['jarak_klaster_lo'] = _loo(ib, 'klaster', 'hambatan_jarak')
    o = o.merge(ib[['caseid', 'jarak_klaster_lo']], on='caseid')
    # --- konteks provinsi
    k = pd.read_csv(C.KONTEKS)
    k['rasio_pkm_per_kec'] = k.puskesmas_2017 / k.kecamatan_2017
    k['tt_per_1000'] = k.tt_rs_total_2017 / k.penduduk_2017 * 1000
    k['pbi_pct_prov'] = (k.jkn_pbi_apbn + k.jkn_pbi_apbd) / k.jkn_penduduk_bpjs * 100
    o = o.merge(k[['kode_prov_v024', 'provinsi', 'p0_kota_mar2017', 'p0_desa_mar2017', 'p0_total_mar2017',
                   'pdrb_kap_adhk2010_2017_ribu', 'rasio_pkm_per_kec', 'tt_per_1000',
                   'pct_pkm_kurang_bidan', 'pbi_pct_prov']], on='kode_prov_v024', how='left')
    o['p0_daerah_mar2017'] = np.where(o.perdesaan == 1, o.p0_desa_mar2017, o.p0_kota_mar2017)
    o = o.drop(columns=['p0_kota_mar2017', 'p0_desa_mar2017'])

    C.OUT.mkdir(exist_ok=True)
    o.to_pickle(C.CACHE / "analisis.pkl")
    o.to_csv(C.OUT / "dataset_analisis.csv", index=False)
    pd.Series({'n_br_5thn': len(d), 'n_hr': len(hr), 'pca_varians': ve}).to_json(C.OUT / "prep_info.json")
    return [f"PREP: {len(o)} kelahiran, {o.shape[1]} variabel, {o.klaster.nunique()} klaster, "
            f"{o.kode_prov_v024.nunique()} provinsi",
            f"PREP: PCA kekayaan non-WASH menjelaskan {ve:.1%} varians; RT tanpa pasangan HR = "
            f"{o.skor_kekayaan_nonwash.isna().sum()}"]


def load():
    p = C.CACHE / "analisis.pkl"
    if not p.exists():
        run()
    return pd.read_pickle(p)
