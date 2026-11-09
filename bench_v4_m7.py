"""Analisis EKSPLORATIF M7 untuk benchmark v4 (deviasi terdokumentasi, BUKAN bagian rencana terkunci rencana-v4).

M7 = himpunan penyesuaian optimal (O-set; Henckel dkk. 2022). Karena DGP benchmark v4 tidak memuat mediator,
O-set pada graf benar = induk Y selain T. Di sini O-set diestimasi dari graf M3 (PC + uji desain + tier), yaitu
paY3 yang sama dengan yang dipakai M6, tanpa digabung dengan induk T.

Data tiap replikasi dibangkitkan PERSIS sama dengan bench_v4.satu (seed dan urutan pemanggilan rng sampai
bangkit() identik), jadi RD_benar dan graf M3 sama dengan baris M0-M6 di per_rep.csv. Lipatan cross-fitting
AIPW memakai aliran rng sendiri, sehingga baris lama tidak berubah.

Letakkan file ini di folder repo (sebelah bench_v4.py), lalu:
    python -u bench_v4_m7.py --icc heterogen --pekerja 3      # sel yang dilaporkan di Tabel 3 (2.400 replikasi)
    python -u bench_v4_m7.py --pekerja 3                      # semua sel (4.800 replikasi)
Keluaran: hasil/benchmark_v4/per_rep_m7.csv (bisa dilanjutkan bila terputus) dan ringkasan di layar.
"""
import argparse
import os
import time
import zlib
import numpy as np
import pandas as pd
import config as C
import baseline as BL
import novelty as N
import bench_v4 as B

OUT = B.OUT


def satu_m7(tugas):
    s, r = tugas
    rng = np.random.default_rng([C.SEED, r, zlib.crc32(B.sel_id(s).encode())])
    ds_df = B.buat_desain(np.random.default_rng([C.SEED, 99]))
    ds = N.Desain(ds_df); w = ds_df.bobot.values
    g = B.dag_teridentifikasi(s['p'], s['kuat'], s['beta_ty'], rng)
    icc = {v: (rng.uniform(0.1, 0.8) if s['icc'] == "heterogen" else float(s['icc'])) for v in g['urut']}
    dat, p1, p0 = B.bangkit(g, ds, icc, rng)
    rd_benar = float(np.average(p1 - p0, weights=w))
    d = pd.concat([ds_df, dat], axis=1)
    V = g['obs'] + ['T', 'Y']; tier = [g['tier'][v] for v in V]
    t0 = time.time()
    _, paY3, _ = B.pc_induk(B.Memo(N.UjiDesain(d, V, "desain", ds, C.NOVELTY['sd_rs_orde'])), V, tier)
    t_pen = time.time() - t0
    Z = sorted(set(paY3))
    rng_lip = np.random.default_rng([C.SEED, r, zlib.crc32(B.sel_id(s).encode()), 7])   # aliran terpisah untuk lipatan
    t0 = time.time()
    rd, se, lo, hi = B.aipw(d, Z, ds, w, B.P['K'], rng_lip)
    return dict(sel=B.sel_id(s), **s, rep=r, metode='M7', n_Z=len(Z), Z=";".join(Z),
                valid=bool(B.adjustment_sah(g['G'], 'T', 'Y', Z)), RD_benar=rd_benar, RD_hat=rd, se=se,
                RD_lo=lo, RD_hi=hi, cakup=bool(lo <= rd_benar <= hi), detik_estimasi=time.time() - t0,
                detik_penemuan=t_pen, n_obs=len(g['obs']), n_laten=len(g['laten']))


def ringkas(f):
    d = pd.read_csv(f)
    d['icc'] = d.icc.astype(str); d['e'] = d.RD_hat - d.RD_benar
    for nama, x in [('semua sel', d)] + [(f"icc={k}", v) for k, v in d.groupby('icc')]:
        n, k = len(x), int(x.valid.sum())
        z = 1.959964; p = k / n; den = 1 + z * z / n
        c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        print(f"{nama:14s} n={n:5d}  valid={100*p:.1f}% [{100*(c-h):.1f}; {100*(c+h):.1f}]  "
              f"|galat|={x.e.abs().mean():.4f}  RMSE={np.sqrt((x.e**2).mean()):.4f}  cakupan={100*x.cakup.mean():.1f}%  "
              f"lebar_IK={(x.RD_hi-x.RD_lo).mean():.4f}  rerata|Z|={x.n_Z.mean():.1f}")


def main():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep", type=int, default=B.P['rep']); ap.add_argument("--pekerja", type=int, default=B.P['pekerja'])
    ap.add_argument("--icc", default=None, help="mis. heterogen; kosong = semua sel")
    ap.add_argument("--ringkas", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "per_rep_m7.csv"
    if a.ringkas:
        ringkas(f); return
    sel = [s for s in B.sel_list() if a.icc is None or str(s['icc']) == a.icc]
    sudah = set()
    if f.exists():
        lama = pd.read_csv(f, usecols=['sel', 'rep']); sudah = set(zip(lama.sel, lama.rep))
    tugas = [(s, r) for s in sel for r in range(a.rep) if (B.sel_id(s), r) not in sudah]
    print(f"{len(tugas)} tugas baru ({len(sudah)} sudah ada), {a.pekerja} pekerja", flush=True)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"
    t0, selesai, galat = time.time(), 0, []
    with ProcessPoolExecutor(max_workers=a.pekerja) as ex:
        fut = {ex.submit(satu_m7, t): t for t in tugas}
        for fu in as_completed(fut):
            try:
                pd.DataFrame([fu.result()]).to_csv(f, mode="a", index=False, header=not f.exists())
            except Exception as e:
                galat.append(f"{B.sel_id(fut[fu][0])} rep {fut[fu][1]}: {e!r}")
            selesai += 1
            if selesai % 20 == 0 or selesai == len(tugas):
                el = time.time() - t0
                print(f"{selesai}/{len(tugas)}, {el/60:.1f} menit, sisa ~{el/selesai*(len(tugas)-selesai)/60:.0f} menit, gagal {len(galat)}", flush=True)
    if galat:
        (OUT / "gagal_m7.txt").write_text("\n".join(galat), encoding="utf-8")
    ringkas(f)


if __name__ == "__main__":
    main()
