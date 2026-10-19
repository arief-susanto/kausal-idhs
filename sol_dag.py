"""MENU SOL-DAG: integrasi MLC-DAG -> SD-Hybrid -> TO-DAG -> estimasi efek (dokumen Tahap 3, bagian 5).
  Langkah 1  MLC v2      : kovarians konstruk/komposit terkoreksi Sigma_V (atau variabel DAG apa adanya tanpa MLC)
  Langkah 2  SD-Hybrid   : skeleton PC dengan uji terkoreksi desain (Rao-Scott / t-desain), hitung n_eff
  Langkah 3  TO-DAG      : pencarian urutan di dalam tier, skor Gauss berskala n_eff, induk dibatasi skeleton
  Langkah 4  Estimasi    : pemisahan sampel per PSU di dalam strata; graf ditemukan di separuh A,
                           AIPW berbobot survei di separuh B, CI bootstrap PSU
Ablasi mematikan satu komponen: tanpa MLC, tanpa koreksi desain, tanpa tier, tanpa pemisahan sampel."""
import itertools
import time
import numpy as np
import pandas as pd
import networkx as nx
import config as C
import baseline as BL
import novelty as N
import causal

P = C.SOL
VARIAN = {
    "SOL-DAG": dict(mlc=True, koreksi=True, tier=True, split=True),
    "SOL tanpa MLC": dict(mlc=False, koreksi=True, tier=True, split=True),
    "SOL tanpa koreksi desain": dict(mlc=True, koreksi=False, tier=True, split=True),
    "SOL tanpa tier": dict(mlc=True, koreksi=True, tier=False, split=True),
    "SOL tanpa pemisahan sampel": dict(mlc=True, koreksi=True, tier=True, split=False),
}


def bagi_psu(d, rng):
    """Separuh PSU di setiap strata ke A (penemuan), sisanya ke B (estimasi)."""
    ps = d[['strata', 'psu']].drop_duplicates()
    a = set()
    for s, g in ps.groupby('strata'):
        k = g.psu.values.copy(); rng.shuffle(k)
        h = len(k) // 2 if len(k) > 1 else int(rng.random() < 0.5)     # strata 1 PSU: acak ke A atau B
        a |= {(s, p) for p in k[:h]}
    return np.array([(s, p) in a for s, p in zip(d.strata, d.psu)])


def skeleton(d_unit, nodes, koreksi, cache=None):
    """Skeleton PC dengan uji terkoreksi desain (koreksi=True) atau uji naif. cache: dict untuk dipakai ulang."""
    kunci = (id(d_unit), tuple(nodes), koreksi)
    if cache is not None and kunci in cache:
        return cache[kunci]
    t0 = BL.mulai_ukur()
    ci = N.UjiDesain(d_unit, nodes, P['uji'], None, P['rs_orde']) if koreksi else BL.UjiCI(d_unit, nodes, "campuran")
    A, _ = BL.pc_skeleton(ci, len(nodes), P['alpha'], P['maks_kondisi'])
    skel = {frozenset((i, j)) for i, j in itertools.combinations(range(len(nodes)), 2) if A[i, j]}
    dt, mem = BL.selesai_ukur(t0)
    hasil = (skel, ci.jumlah, dt, mem)
    if cache is not None:
        cache[kunci] = hasil
    return hasil


def temukan(d_unit, nodes, tier, opsi, S_mlc=None, cache=None):
    """Langkah 2-3. d_unit: data unit (skor konstruk untuk node MLC). S_mlc: Sigma_V terkoreksi (None = tanpa MLC).
    -> (G indeks, info)"""
    skel, n_uji, dt_s, mem_s = skeleton(d_unit, nodes, opsi['koreksi'], cache)
    t0 = BL.mulai_ukur()
    n = len(d_unit)
    if opsi['koreksi']:
        dbar, n_kish, _ = N.deff_umum(d_unit, nodes, N.Desain(d_unit)); n_eff = n_kish / dbar
    else:
        dbar, n_eff = 1.0, n
    if S_mlc is not None:
        sk = N.SkorKov(S_mlc, n_eff)          # fit dan penalti pada skala n_eff
    else:
        sk = N.SkorW(d_unit, nodes, "gauss", opsi['koreksi'], n_eff, "n_eff" if opsi['koreksi'] else "n")
    t_ = tier if opsi['tier'] else [0] * len(nodes)
    G, urutan, F, jejak = N.TODAG(sk, P['maks_induk'], boleh=skel).cari(nodes, t_, P['eksak_maks'])
    dt, mem = BL.selesai_ukur(t0)
    return G, dict(jumlah_uji=n_uji, sisi_skeleton=len(skel), delta_bar=dbar, n_eff=n_eff, skor=F,
                   skor_lokal=len(sk.cache), langkah=len(jejak), detik_penemuan=dt + dt_s, memori_MB=max(mem, mem_s))


def efek_aipw(G, dB, T, Y, B, rng):
    """AIPW berbobot survei dengan adjustment set backdoor dari G; CI bootstrap PSU."""
    if T not in G or Y not in G or Y not in nx.descendants(G, T):
        return dict(RD=0.0, RD_lo=0.0, RD_hi=0.0, RR=1.0, RR_lo=1.0, RR_hi=1.0, Z=[],
                    catatan="tidak ada jalur berarah T->Y di graf: efek = 0")
    Z, _, _ = causal.adjustment(G, T, Y, [])
    r, _, _ = causal.estimate(dB, T, Y, Z)
    out = dict(RD=r['aipw_RD'], RR=r['aipw_RR'], Z=Z, catatan="", RD_lo=np.nan, RD_hi=np.nan, RR_lo=np.nan, RR_hi=np.nan)
    if B:
        bs = causal.bootstrap(dB, T, Y, Z, B, rng)
        out.update(RD_lo=bs.aipw_RD.quantile(.025), RD_hi=bs.aipw_RD.quantile(.975),
                   RR_lo=bs.aipw_RR.quantile(.025), RR_hi=bs.aipw_RR.quantile(.975))
    return out


def jalankan(spec, opsi, d_mlc, obs, d_v, V, B, rng, cache=None, mask_A=None, R=None, biner=None, tier_v=None):
    """Satu varian SOL. d_mlc/obs: data & node teramati untuk jalur MLC; d_v/V: data & variabel DAG (tanpa MLC).
    mask_A: pembagian PSU (dipakai bersama antar-varian agar adil). -> dict hasil"""
    T, Y = spec['T'], spec['Y']
    dat = d_mlc if opsi['mlc'] else d_v
    A = mask_A if (opsi['split'] and mask_A is not None) else (bagi_psu(dat, rng) if opsi['split'] else None)
    dA = dat[A].reset_index(drop=True) if A is not None else dat
    dB = dat[~A].reset_index(drop=True) if A is not None else dat
    t0 = time.time()
    if opsi['mlc']:
        tu = BL.mulai_ukur()
        m = N.bangun_mlc(dA, obs, R if A is None else None, biner if A is None else None)
        dt_m, mem_m = BL.selesai_ukur(tu)
        nodes, tier = m['Vm'], m['tier']
        uA = pd.concat([dA, m['skor']], axis=1); uB = pd.concat([dB, N.skor_mlc(m, dB)], axis=1)
        G, inf = temukan(uA, nodes, tier, opsi, m['S'], cache)
        inf['detik_penemuan'] += dt_m; inf['memori_MB'] = max(inf['memori_MB'], mem_m)
        inf.update(reflektif=', '.join(m['refl']) or '-', komposit=', '.join(m['komposit']) or '-',
                   dipecah=', '.join(m['pecah']) or '-')
    else:
        nodes, tier = V, (tier_v or [C.TIER[v] for v in V])
        uA, uB = dA, dB
        G, inf = temukan(uA, nodes, tier, opsi, None, cache)
    Gb = nx.relabel_nodes(G, dict(enumerate(nodes)))
    e = efek_aipw(Gb, uB, T, Y, B, rng)
    return dict(G=Gb, nodes=nodes, n_A=len(dA), n_B=len(dB), **inf, **e, detik_total=time.time() - t0)


# ================================================================== menu (data nyata)
def run(df, nama=None, varian=tuple(VARIAN), progress=None):
    rng = np.random.default_rng(C.SEED); lines = []
    N.MLC_DATA[0] = df
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = C.OUT / "sol_dag" / n; out.mkdir(parents=True, exist_ok=True)
        d_v, V, G0 = BL.siapkan(df, spec)
        d_m, obs, cols = N.data_mlc(spec, df)
        R, biner = N.korelasi_laten(d_m, cols)
        mA_m, mA_v = bagi_psu(d_m, rng), bagi_psu(d_v, rng)
        cache, rows = {}, []
        for vn in varian:
            if progress:
                progress(f"{n}: {vn} ...")
            o = VARIAN[vn]
            h = jalankan(spec, o, d_m, obs, d_v, V, P['boot'], rng, cache,
                         mA_m if o['mlc'] else mA_v, R, biner)
            rows.append(dict(varian=vn, **{k: v for k, v in o.items()}, node=len(h['nodes']),
                             sisi=h['G'].number_of_edges(), sisi_skeleton=h['sisi_skeleton'],
                             jumlah_uji=h['jumlah_uji'], n_eff=h['n_eff'], n_A=h['n_A'], n_B=h['n_B'],
                             RD=h['RD'], RD_lo=h['RD_lo'], RD_hi=h['RD_hi'], RR=h['RR'], RR_lo=h['RR_lo'],
                             RR_hi=h['RR_hi'], detik_penemuan=h['detik_penemuan'], memori_MB=h['memori_MB'],
                             adjustment=', '.join(h['Z']) or '-', catatan=h['catatan'] or '-',
                             reflektif=h.get('reflektif', '-'), komposit=h.get('komposit', '-'),
                             dipecah=h.get('dipecah', '-')))
            pre = "sol" if vn == "SOL-DAG" else None
            if pre:
                pd.DataFrame(list(h['G'].edges()), columns=['dari', 'ke']).to_csv(out / "sol_dag.csv", index=False)
                BL.gambar(h['nodes'], h['G'].edges(), [], spec, f"SOL-DAG ({len(h['nodes'])} node)", out / "sol_graf.png")
            lines.append(f"SOL[{n}] {vn}: node={len(h['nodes'])} sisi={h['G'].number_of_edges()} "
                         f"skeleton={h['sisi_skeleton']} RD={h['RD']:+.4f} [{h['RD_lo']:+.4f},{h['RD_hi']:+.4f}] "
                         f"detik={h['detik_penemuan']:.2f} memori={h['memori_MB']:.1f}MB")
        tab = pd.DataFrame(rows)
        tab.to_csv(out / "sol_varian.csv", index=False)
        # pembanding: baseline dan kandidat pada analisis yang sama
        bnd = [tab.assign(kode=['SOL' if v == 'SOL-DAG' else 'SOL-' for v in tab.varian]).rename(columns={'varian': 'metode'})]
        f = C.OUT / "baseline" / n / "rangkuman.csv"
        if f.exists():
            bnd.append(pd.read_csv(f)[['kode', 'metode', 'sisi', 'RD', 'RD_lo', 'RD_hi', 'detik_penemuan', 'memori_MB']])
        for m_ in ("sd_hybrid", "to_dag", "mlc_dag"):
            f = C.OUT / "novelty" / m_ / n / "banding.csv"
            if f.exists():
                b = pd.read_csv(f); bnd.append(b[b.kode.str.startswith('N')][['kode', 'metode', 'sisi', 'RD', 'RD_lo',
                                                                              'RD_hi', 'detik_penemuan', 'memori_MB']])
        bd = pd.concat(bnd, ignore_index=True)
        bd = bd[['kode', 'metode', 'node', 'sisi', 'RD', 'RD_lo', 'RD_hi', 'detik_penemuan', 'memori_MB']
                if 'node' in bd else ['kode', 'metode', 'sisi', 'RD', 'RD_lo', 'RD_hi', 'detik_penemuan', 'memori_MB']]
        bd.to_csv(out / "sol_banding.csv", index=False)
        BL.forest(bd.assign(RD_lo=bd.RD_lo.fillna(bd.RD), RD_hi=bd.RD_hi.fillna(bd.RD)), spec['T'], spec['Y'],
                  out / "sol_banding.png")
    return lines


# ================================================================== SOL-DAG v2 (pra-registrasi, v2/sol_v2.py)
import sys as _sys
_sys.path.insert(0, str(C.ROOT / "v2"))
import sol_v2 as V2          # dipakai apa adanya (hash tercatat di v2/HASH_KODE_v2.txt)

VARIAN_V2 = {"SOL v2 (desain)": dict(mlc=False, design=True), "SOL v2 naif": dict(mlc=False, design=False),
             "SOL v2 + MLC": dict(mlc=True, design=True)}


def run_v2(df, nama=None, varian=tuple(VARIAN_V2), progress=None):
    """SOL v2: graf (PC-stable + tier, uji-t desain) hanya memilih himpunan penyesuaian; efek T->Y selalu
    diestimasi dengan AIPW cross-fitting per PSU (K lipatan), SE fungsi pengaruh + linearisasi desain."""
    lines = []; Pv = C.SOL_V2
    N.MLC_DATA[0] = df
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = C.OUT / "sol_dag" / n; out.mkdir(parents=True, exist_ok=True)
        T, Y = spec['T'], spec['Y']
        d_v, V, _ = BL.siapkan(df, spec)
        rows = []
        for vn in varian:
            o = VARIAN_V2[vn]
            if progress:
                progress(f"{n}: {vn} ...")
            t0 = BL.mulai_ukur()
            if o['mlc']:
                d_m, obs, _ = N.data_mlc(spec, df)
                m = N.bangun_mlc(d_m, obs)
                dat = pd.concat([d_m, m['skor']], axis=1); nodes, tier = m['Vm'], m['tier']
            else:
                dat, nodes, tier = d_v, V, [C.TIER[v] for v in V]
            D = V2.make_D(dat[nodes].to_numpy(float), dat.bobot, dat.psu, dat.strata)
            r = V2.query_effect(D, nodes.index(T), nodes.index(Y), tier, alpha=Pv['alpha'], K=Pv['K'],
                                design=o['design'], seed=C.SEED)
            dt, mem = BL.selesai_ukur(t0)
            G = nx.relabel_nodes(r['G'], dict(enumerate(nodes)))
            und = [(nodes[a], nodes[b]) for a, b in r['U']]
            rows.append(dict(varian=vn, node=len(nodes), n=D['n'], sisi=G.number_of_edges(), tak_berarah=len(und),
                             RD=r['rd'], RD_lo=r['lo'], RD_hi=r['hi'], himpunan_kandidat=r['n_set'],
                             RD_min=r['rd_set'][0], RD_max=r['rd_set'][1],
                             induk_T=', '.join(G.predecessors(T)) or '-', detik=dt, memori_MB=mem))
            if vn == "SOL v2 (desain)":
                pd.DataFrame([(a, b, '->') for a, b in G.edges()] + [(a, b, '-') for a, b in und],
                             columns=['dari', 'ke', 'jenis']).to_csv(out / "sol_v2_graf.csv", index=False)
                BL.gambar(nodes, G.edges(), und, spec, f"SOL v2 (uji-t desain, α={Pv['alpha']})", out / "sol_v2_graf.png")
            lines.append(f"SOLv2[{n}] {vn}: node={len(nodes)} sisi={G.number_of_edges()}+{len(und)} "
                         f"RD={r['rd']:+.4f} [{r['lo']:+.4f},{r['hi']:+.4f}] induk T={rows[-1]['induk_T']} "
                         f"{dt:.1f}s {mem:.1f}MB")
        pd.DataFrame(rows).to_csv(out / "sol_v2.csv", index=False)
    return lines
