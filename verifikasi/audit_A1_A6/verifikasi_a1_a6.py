"""Verifikasi ulang perbaikan audit A1-A6 (commit 74eb7a4, 10-10-2026) pada kode dan data sekarang.

Skrip ini hanya membaca kode dan data; seluruh luaran ditulis ke folder ini (hasil/ tidak disentuh).
  A1  semua modul memakai config.py (bukan config_old.py)
  A2  simulasi S={z}: z benar-benar confounder x dan y; H0 bersyarat tetap benar
  A3  aliran acak per analisis: hasil satu analisis tidak bergantung pada analisis lain yang ikut dijalankan
  A4  MLC-DAG (novelty dan benchmark) memakai n_eff, bukan n mentah
  A5  delta_bar dihitung tanpa variabel konteks tier 0
  A6  treatment analisis lain tidak masuk node MLC

Pakai (dari folder proyek kausal_idhs):
    python dok_disertasi/verifikasi_audit/verifikasi_a1_a6.py [--rep-a2 500] [--boot-a3 30]
"""
import argparse
import ast
import hashlib
import importlib
import json
import os
import platform
import re
import sys
import tempfile
import time
import warnings
from datetime import datetime
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = os.environ["OPENBLAS_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = "1"
warnings.filterwarnings("ignore")
SINI = Path(__file__).resolve().parent
PROYEK = SINI.parents[1]
sys.path.insert(0, str(PROYEK)); os.chdir(PROYEK)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import config as C  # noqa: E402
import baseline as BL  # noqa: E402
import novelty as N  # noqa: E402
import prep  # noqa: E402

a = argparse.ArgumentParser()
a.add_argument("--rep-a2", type=int, default=500)
a.add_argument("--boot-a3", type=int, default=30)
ARG = a.parse_args()
HASIL = {}          # kode -> dict(status, ringkas, rincian)
t0 = time.time()


def catat(kode, lulus, ringkas, **rinci):
    HASIL[kode] = dict(status="LULUS" if lulus else "GAGAL", ringkas=ringkas, **rinci)
    print(f"[{kode}] {'LULUS' if lulus else 'GAGAL'}: {ringkas}", flush=True)


# ------------------------------------------------------------------ A1
# (a) statis: tidak ada impor config_old di modul aktif; (b) runtime: objek C di tiap modul = modul config;
# (c) dampak: nilai yang berbeda antara config.py dan config_old.py (yang dulu diam-diam terpakai).
AKTIF = [p for p in sorted(PROYEK.glob("*.py"))
         if not re.search(r"(_sebelum_audit|_audit|config_old)\.py$", p.name)]
impor_lama = []
for p in AKTIF:
    try:
        pohon = ast.parse(p.read_text(encoding="utf-8-sig"))
    except SyntaxError:
        continue
    for n in ast.walk(pohon):
        if isinstance(n, ast.Import) and any(x.name == "config_old" for x in n.names):
            impor_lama.append(p.name)
        if isinstance(n, ast.ImportFrom) and n.module == "config_old":
            impor_lama.append(p.name)
mod_runtime = {}
for m in ["baseline", "novelty", "benchmark", "sol_dag", "narasi", "laporan", "eda", "prep"]:
    try:
        mm = importlib.import_module(m)
        mod_runtime[m] = getattr(mm, "C", None) is C
    except Exception as e:  # modul opsional
        mod_runtime[m] = f"tidak dapat diimpor: {type(e).__name__}"
import config_old as CO  # noqa: E402
beda_cfg = []
for nama in ["NOVELTY", "BENCH", "SOL", "SOL_V2", "TIER", "BASELINE", "KAUSAL"]:
    x, y = getattr(C, nama, None), getattr(CO, nama, None)
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y), key=str):
            if x.get(k, "∅") != y.get(k, "∅"):
                beda_cfg.append(dict(objek=nama, kunci=str(k), config_old=repr(y.get(k, "∅")), config=repr(x.get(k, "∅"))))
pd.DataFrame(beda_cfg).to_csv(SINI / "A1_beda_config.csv", index=False)
ok_runtime = all(v is True for v in mod_runtime.values() if not isinstance(v, str))
catat("A1", not impor_lama and ok_runtime,
      f"{len(AKTIF)} modul aktif dipindai, {len(impor_lama)} masih mengimpor config_old; "
      f"{sum(v is True for v in mod_runtime.values())} modul terimpor memakai objek config yang sama; "
      f"{len(beda_cfg)} nilai config.py berbeda dari config_old.py (dulu tidak terpakai)",
      impor_lama=impor_lama, runtime=mod_runtime, n_beda_config=len(beda_cfg))

# ------------------------------------------------------------------ data bersama
df = prep.load()
N.MLC_DATA[0] = df
ANALISIS = list(C.ANALISIS.items())

# ------------------------------------------------------------------ A2
# Generator persis seperti novelty.simulasi_uji (efek = 0), ditambah kasus diagnostik yang tidak dilaporkan
# di log: pasangan berkonfounder (xz, yz) TANPA pengondisian. Bila z benar confounder, uji ini harus sering
# menolak; dengan pengondisian pada z harus kembali ke sekitar alpha.
nama_a2, spec_a2 = ANALISIS[0]
d2, V2, _ = BL.siapkan(df, spec_a2)
base = d2[["bobot", "strata", "psu"]].reset_index(drop=True)
ds = N.Desain(base)
icc, alpha, cz = C.NOVELTY["sim_icc"], 0.05, C.NOVELTY.get("sim_kuat_z", 0.6)
sz = np.sqrt(1 - cz ** 2)
KASUS = [  # label, a, b, S, peran
    ("kontinu: pasangan z, S=∅ (diagnostik)", "xzc", "yzc", (), "harus jauh di atas α"),
    ("kontinu: pasangan z, S={z} (versi audit)", "xzc", "yzc", ("zc",), "≈ α"),
    ("kontinu: pasangan lama, S={z} (versi pra-audit)", "xc", "yc", ("zc",), "≈ α"),
    ("kontinu: S=∅", "xc", "yc", (), "≈ α"),
    ("biner: pasangan z, S=∅ (diagnostik)", "xzb", "yzb", (), "harus jauh di atas α"),
    ("biner: pasangan z, S={z} (versi audit)", "xzb", "yzb", ("zb",), "≈ α"),
    ("biner: pasangan lama, S={z} (versi pra-audit)", "xb", "yb", ("zb",), "≈ α"),
    ("biner: S=∅", "xb", "yb", (), "≈ α"),
]
rng = np.random.default_rng([C.SEED, 2])
tol = np.zeros((len(KASUS), 2), int)
putus = np.zeros((ARG.rep_a2, len(KASUS)), bool)
pval = np.zeros((ARG.rep_a2, len(KASUS)))          # p terkoreksi per replikasi (cek kesetaraan pasangan)
stat = np.zeros((ARG.rep_a2, len(KASUS)))          # p naif per replikasi
for i in range(ARG.rep_a2):
    lat = {v: np.sqrt(icc) * rng.standard_normal(ds.npsu)[ds.pc] + np.sqrt(1 - icc) * rng.standard_normal(len(base))
           for v in ("x", "y", "z")}
    g = {}
    for v, l in lat.items():
        g[v + "c"] = l; g[v + "b"] = (l > 0).astype(float)
    g["xzc"] = cz * lat["z"] + sz * lat["x"]; g["yzc"] = cz * lat["z"] + sz * lat["y"]
    zs = 2 * g["zb"] - 1
    g["xzb"] = (cz * zs + sz * lat["x"] > 0).astype(float); g["yzb"] = (cz * zs + sz * lat["y"] > 0).astype(float)
    x = base.assign(**g); cols = list(g); ix = {c: k for k, c in enumerate(cols)}
    naif, kor = BL.UjiCI(x, cols, "campuran"), N.UjiDesain(x, cols, "desain", ds)
    for k, (_, aa, bb, S, _) in enumerate(KASUS):
        Si = tuple(ix[s] for s in S)
        pn = naif.p(ix[aa], ix[bb], Si)
        pk = kor.t_desain(ix[aa], ix[bb], Si) if aa.endswith("c") else kor.rao_scott(ix[aa], ix[bb], Si, orde=2)
        tol[k] += [pn < alpha, pk < alpha]; putus[i, k] = pk < alpha; pval[i, k] = pk; stat[i, k] = pn
from scipy.stats import binomtest  # noqa: E402


def wilson(k, n, z=1.959964):
    p = k / n; d = 1 + z ** 2 / n; c = (p + z ** 2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return c - h, c + h


A2 = pd.DataFrame([dict(kasus=k[0], harapan=k[4], replikasi=ARG.rep_a2, alpha=alpha,
                        tolak_naif=tol[j, 0] / ARG.rep_a2, tolak_terkoreksi=tol[j, 1] / ARG.rep_a2,
                        ci95_lo=wilson(tol[j, 1], ARG.rep_a2)[0], ci95_hi=wilson(tol[j, 1], ARG.rep_a2)[1],
                        p_binom_vs_alpha=binomtest(int(tol[j, 1]), ARG.rep_a2, alpha).pvalue)
                   for j, k in enumerate(KASUS)])
# Kesetaraan struktural: pada kasus kontinu, residu (cz*z + sz*x) atas z = sz * residu x atas z, sehingga
# statistik uji bersyarat untuk pasangan z identik dengan pasangan lama (skala tidak memengaruhi korelasi parsial).
setara = dict(kontinu_maks_beda_p_terkoreksi=float(np.abs(pval[:, 1] - pval[:, 2]).max()),
              kontinu_maks_beda_p_naif=float(np.abs(stat[:, 1] - stat[:, 2]).max()),
              kontinu_keputusan_sama=float((putus[:, 1] == putus[:, 2]).mean()),
              biner_maks_beda_p_terkoreksi=float(np.abs(pval[:, 5] - pval[:, 6]).max()),
              biner_keputusan_sama=float((putus[:, 5] == putus[:, 6]).mean()))
pd.DataFrame({"replikasi": np.arange(ARG.rep_a2), **{f"p_{KASUS[j][1]}_{KASUS[j][2]}_{'S' + ''.join(KASUS[j][3]) if KASUS[j][3] else 'S0'}": pval[:, j]
                                                      for j in range(len(KASUS))}}).to_csv(SINI / "A2_p_per_replikasi.csv", index=False)
A2.to_csv(SINI / "A2_simulasi_confounder.csv", index=False)
sepakat = lambda i, j: float((putus[:, i] == putus[:, j]).mean())
ag_audit, ag_lama = sepakat(1, 3), sepakat(2, 3)
diag_c, diag_b = A2.tolak_terkoreksi[0], A2.tolak_terkoreksi[4]
kal = A2.tolak_terkoreksi[[1, 5]].between(0.02, 0.09).all()
catat("A2", diag_c > 0.5 and diag_b > 0.5 and kal,
      f"pasangan z tanpa pengondisian ditolak {diag_c:.1%} (kontinu) dan {diag_b:.1%} (biner) -> z benar confounder; "
      f"dengan S={{z}} kembali ke {A2.tolak_terkoreksi[1]:.1%} dan {A2.tolak_terkoreksi[5]:.1%}. "
      f"Namun keputusan S={{z}} kontinu sama dengan S=∅ pada {ag_audit:.1%} replikasi (versi pra-audit {ag_lama:.1%}): "
      "perbandingan baris log S={z} vs S=∅ tidak dapat membedakan versi lama dan baru",
      analisis=nama_a2, replikasi=ARG.rep_a2, icc=icc, muatan_z=cz,
      sepakat_kontinu_audit=ag_audit, sepakat_kontinu_pra_audit=ag_lama,
      sepakat_biner_audit=sepakat(5, 7), sepakat_biner_pra_audit=sepakat(6, 7), **setara)

# ------------------------------------------------------------------ A3
# Jalankan N2 TO-DAG (memakai rng untuk bootstrap) untuk (a) semua analisis dan (b) hanya analisis ke-2 dan
# ke-3, lewat novelty.run() sungguhan; folder luaran dialihkan ke direktori sementara. Lalu tiru perilaku
# pra-audit (satu rng bersama) untuk menunjukkan bahwa bug-nya memang ada.
BOOT_ASLI = N.P["boot"]
N.P["boot"] = ARG.boot_a3
tmp = Path(tempfile.mkdtemp(prefix="verif_a3_"))
asli_folder = N.folder


def jalankan(label, nama=None):
    def f(metode, n):
        out = tmp / label / n; out.mkdir(parents=True, exist_ok=True); return out
    N.folder = f
    try:
        return N.run(df, "to_dag", nama)
    finally:
        N.folder = asli_folder


WAKTU = {"detik_penemuan", "memori_MB", "detik", "memori"}   # kolom pengukuran waktu, wajar berbeda


def isi_hasil(label, n):
    """Isi berkas hasil tanpa kolom/baris pengukuran waktu dan memori."""
    out = {}
    for p in sorted((tmp / label / n).glob("*.csv")):
        x = pd.read_csv(p, float_precision="round_trip")
        x = x.drop(columns=[c for c in x if c in WAKTU or c.startswith(("rank_detik", "rank_memori"))
                            or c in ("peringkat_rata2", "terbaik")])   # peringkat memakai waktu -> dicatat terpisah
        if p.name == "to_info.csv" and "nilai" in x:
            x = x[~x.iloc[:, 0].astype(str).str.contains("detik|memori|waktu", case=False)]
        out[p.name] = x.reset_index(drop=True)
    return out


def ci(rows):
    return tuple(round(float(r[c]), 12) for r in rows for c in ("RD", "RD_lo", "RD_hi") if c in r)


jalankan("semua")
a3 = []
for k in range(1, len(ANALISIS)):
    n = ANALISIS[k][0]
    jalankan(f"satu_{n}", n)
    A_, B_ = isi_hasil("semua", n), isi_hasil(f"satu_{n}", n)
    beda = [f for f in A_ if f not in B_ or not A_[f].equals(B_[f])]
    tb = lambda lab: pd.read_csv(tmp / lab / n / "banding.csv").pipe(lambda x: " ".join(x.loc[x.terbaik == True, x.columns[0]].astype(str)) if "terbaik" in x else "")
    a3.append(dict(analisis=n, berkas_dibandingkan=len(A_), identik=not beda, berkas_beda=" ".join(beda),
                   terbaik_semua=tb("semua"), terbaik_sendiri=tb(f"satu_{n}")))
# pra-audit: SATU rng untuk semua analisis (berurutan) vs rng baru bila analisis dijalankan sendiri
rng_lama = np.random.default_rng(C.SEED)
for k, (n, spec) in enumerate(ANALISIS):
    d, V, G = BL.siapkan(df, spec)
    for lab in ("lama", "lama1"):
        (tmp / lab / n).mkdir(parents=True, exist_ok=True)
    rows, _ = N.to_dag(d, V, G, spec, tmp / "lama" / n, ARG.boot_a3, rng_lama)
    rows1, _ = N.to_dag(d, V, G, spec, tmp / "lama1" / n, ARG.boot_a3, np.random.default_rng(C.SEED))
    if k >= 1:
        r = a3[k - 1]
        r["pra_audit_berbeda"] = ci(rows) != ci(rows1)
        r["RD_CI_pra_audit_semua"] = str(ci(rows)); r["RD_CI_pra_audit_sendiri"] = str(ci(rows1))
A3 = pd.DataFrame(a3); A3["terbaik_berpindah"] = A3.terbaik_semua != A3.terbaik_sendiri
A3.to_csv(SINI / "A3_aliran_acak.csv", index=False)
catat("A3", bool(A3.identik.all()),
      f"berkas hasil N2 identik antara 'jalankan semua' dan 'jalankan satu' pada {int(A3.identik.sum())}/{len(A3)} "
      f"analisis (kolom waktu/memori diabaikan); tiruan perilaku pra-audit (satu rng bersama) memberi RD/CI bootstrap "
      f"berbeda pada {int(A3.pra_audit_berbeda.sum())}/{len(A3)} analisis. Terpisah dari rng: label 'terbaik' di banding.csv "
      f"berpindah pada {int(A3.terbaik_berpindah.sum())}/{len(A3)} analisis karena peringkat memakai waktu komputasi",
      bootstrap=ARG.boot_a3, folder_sementara=str(tmp))
N.P["boot"] = BOOT_ASLI

# ------------------------------------------------------------------ A4, A5, A6 (per analisis, data nyata)
a4, a5, a6 = [], [], []
for n, spec in ANALISIS:
    # A6: node MLC dengan dan tanpa treatment analisis lain
    N.P["mlc_treatment_lain"] = True
    _, obs_lama, _ = N.data_mlc(spec)
    N.P["mlc_treatment_lain"] = False
    dd, obs, cols = N.data_mlc(spec)
    T = spec["T"]
    a6.append(dict(analisis=n, T=T, treatment_pra_audit=" ".join(v for v in obs_lama if v.startswith("T_")),
                   treatment_audit=" ".join(v for v in obs if v.startswith("T_")),
                   treatment_lain_tersisa=" ".join(v for v in obs if v.startswith("T_") and v != T),
                   tersisa_di_DAG_pakar=all(v in BL.build_dag(spec) for v in obs if v.startswith("T_") and v != T)))
    # A4: n yang dipakai skor/uji MLC
    tier_kol = {c: C.TIER[c] if c in C.TIER else C.TIER[next(kk for kk, v in C.MLC_KONSTRUK.items() if c in v)]
                for c in cols}
    db, nk, _ = N.deff_umum(dd, [c for c in cols if tier_kol[c] > 0] or cols, N.Desain(dd))
    a4.append(dict(analisis=n, n_mentah=len(dd), n_kish=round(nk, 1), delta_bar=round(db, 3), n_eff=round(nk / db, 1),
                   rasio_n_eff_per_n=round(nk / db / len(dd), 3)))
    # A5: delta_bar pada node baseline/N1 dengan dan tanpa variabel konteks tier 0
    d, V, _ = BL.siapkan(df, spec)
    ds_ = N.Desain(d)
    N.P["deff_dengan_konteks"] = True
    db_lama, nk5, dv = N.deff_umum(d, V, ds_)
    N.P["deff_dengan_konteks"] = False
    db_baru, _, _ = N.deff_umum(d, V, ds_)
    manual = float(np.nanmean(dv[[v for v in V if C.TIER.get(v, 1) > 0]]))
    t0v = [v for v in V if C.TIER.get(v, 1) == 0]
    a5.append(dict(analisis=n, variabel_tier0=" ".join(t0v), deff_maks_tier0=round(float(dv[t0v].max()), 2) if t0v else np.nan,
                   delta_bar_pra_audit=round(db_lama, 3), delta_bar_audit=round(db_baru, 3),
                   n_eff_pra_audit=round(nk5 / db_lama, 0), n_eff_audit=round(nk5 / db_baru, 0),
                   cocok_manual=abs(manual - db_baru) < 1e-12))
N.P.pop("mlc_treatment_lain", None); N.P.pop("deff_dengan_konteks", None)
A4, A5, A6 = pd.DataFrame(a4), pd.DataFrame(a5), pd.DataFrame(a6)
A4.to_csv(SINI / "A4_n_eff_mlc.csv", index=False); A5.to_csv(SINI / "A5_delta_bar.csv", index=False)
A6.to_csv(SINI / "A6_node_mlc.csv", index=False)
src_b = (PROYEK / "benchmark.py").read_text(encoding="utf-8-sig")
src_n = (PROYEK / "novelty.py").read_text(encoding="utf-8-sig")
pakai_mentah = len(re.findall(r"temukan\([^)]*len\(d{1,2}\)", src_b + src_n))
catat("A4", pakai_mentah == 0 and bool((A4.n_eff < A4.n_mentah).all()),
      f"tidak ada lagi pemanggilan temukan(..., len(d)) di novelty.py/benchmark.py; n_eff MLC = "
      f"{A4.rasio_n_eff_per_n.min():.0%}–{A4.rasio_n_eff_per_n.max():.0%} dari n mentah",
      pemanggilan_n_mentah=pakai_mentah)
A5["arah"] = np.where(A5.delta_bar_audit < A5.delta_bar_pra_audit, "turun", "naik")
catat("A5", bool(A5.cocok_manual.all()),
      f"delta_bar berubah dari rentang {A5.delta_bar_pra_audit.min():.2f}–{A5.delta_bar_pra_audit.max():.2f} menjadi "
      f"{A5.delta_bar_audit.min():.2f}–{A5.delta_bar_audit.max():.2f}; implementasi cocok dengan hitungan manual "
      f"(rerata deff variabel tier > 0) pada {int(A5.cocok_manual.sum())}/{len(A5)} analisis. Arah perubahan: "
      f"turun pada {int((A5.arah == 'turun').sum())}, naik pada {int((A5.arah == 'naik').sum())} analisis")
catat("A6", bool(A6.tersisa_di_DAG_pakar.all()),
      f"treatment analisis lain di node MLC: pra-audit {sum(len(s.split()) - 1 for s in A6.treatment_pra_audit)} "
      f"(total atas {len(A6)} analisis), sesudah audit {sum(len(s.split()) for s in A6.treatment_lain_tersisa)}, "
      "seluruhnya treatment yang memang node DAG pakar analisis tersebut (pengecualian yang disengaja)")

# ------------------------------------------------------------------ jejak
git = lambda *x: os.popen("git " + " ".join(x)).read().strip()
meta = dict(waktu=datetime.now().astimezone().isoformat(timespec="seconds"), menit=round((time.time() - t0) / 60, 1),
            commit_HEAD=git("rev-parse", "--short", "HEAD"), python=platform.python_version(), numpy=np.__version__,
            pandas=pd.__version__, sha256_novelty=hashlib.sha256((PROYEK / "novelty.py").read_bytes()).hexdigest(),
            sha256_benchmark=hashlib.sha256((PROYEK / "benchmark.py").read_bytes()).hexdigest(),
            sha256_config=hashlib.sha256((PROYEK / "config.py").read_bytes()).hexdigest(), hasil=HASIL)
(SINI / "ringkasan_verifikasi.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(f"selesai dalam {meta['menit']} menit")
