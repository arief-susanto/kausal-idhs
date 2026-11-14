"""E8b injeksi kesalahan yang diturunkan dari taksonomi eksternal (review 14-11-2026, M1b).

Berbeda dengan E8, jenis kesalahan di sini tidak berasal dari kejadian dalam proyek, melainkan dari kategori kesalahan
konfigurasi Yin dkk. (SOSP 2011): (a) parameter bernilai sah tetapi salah, (b) parameter hilang/salah eja,
(c) inkonsistensi antarbagian (nilai ditimpa di modul lain), (d) komponen basi (modul dependensi versi lain), dan
(e) lingkungan/kompatibilitas pada saat run dilanjutkan. Target setiap operator dipilih acak dengan benih tetap dari
parameter yang dibaca benchmark v4, sehingga penulis tidak memilih target secara langsung. Set ini TIDAK buta: operator
dan detektor tetap dirancang oleh penulis yang sama.

Detektor = detektor E8 (injeksi_kesalahan.py) + D1r penjaga runtime (lihat negatif_palsu_impor.py).
Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/injeksi_eksternal.py
Keluaran: naskah/03_reproduksibilitas/tabel/E8b_injeksi_eksternal.csv
"""
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKRIP = Path(__file__).resolve().parent
sys.path.insert(0, str(SKRIP))
import injeksi_kesalahan as I  # noqa: E402

BENIH = 20261114
# kandidat parameter bernilai sah yang dibaca analisis benchmark v4 (bukan jumlah rep/pekerja), dengan nilai sah lain
KANDIDAT_A = {"BENCH_V4 alpha": ("alpha=0.05,                     # alpha uji untuk M2/M3",
                                  "alpha=0.10,                     # alpha uji untuk M2/M3"),
              "BENCH_V4 maks_kondisi": ("    maks_kondisi=3,\n    laten_frac", "    maks_kondisi=2,\n    laten_frac"),
              "BENCH_V4 laten_frac": ("laten_frac=0.15,", "laten_frac=0.20,"),
              "NOVELTY sd_rs_orde": ("sd_rs_orde=2,", "sd_rs_orde=1,"),
              "SEED": ("SEED = 2017", "SEED = 2018")}
MODUL_DEP = ["baseline.py", "novelty.py", "causal.py"]          # modul yang diimpor bench_v4 dan membaca config


def _cfg(sb, lama, baru):
    f = sb / "config.py"; t = f.read_text(encoding="utf-8"); assert t.count(lama) >= 1, lama
    f.write_text(t.replace(lama, baru, 1), encoding="utf-8")


def operator(rng):
    target_a = rng.sample(sorted(KANDIDAT_A), 3)
    target_c = rng.choice(MODUL_DEP)
    ops = {}
    for k in target_a:
        ops[f"a. nilai sah tetapi salah: {k}"] = (lambda sb, k=k: _cfg(sb, *KANDIDAT_A[k]))
    ops["b. kunci parameter salah eja (NOVELTY sd_rs_orde)"] = lambda sb: _cfg(sb, "sd_rs_orde=2,", "sd_rs_ordo=2,")

    def tindih(sb, m=target_c):
        f = sb / m; t = f.read_text(encoding="utf-8")
        pos = re.search(r"^import config as C.*$", t, re.M); assert pos, m
        f.write_text(t[:pos.end()] + "\nC.BENCH_V4['alpha'] = 0.10   # ditimpa saat impor\n" + t[pos.end():], encoding="utf-8")
    ops[f"c. nilai ditimpa saat impor di {target_c}"] = tindih

    def basi(sb):
        t = (sb / "novelty_sebelum_audit.py").read_text(encoding="utf-8")   # impor dibetulkan: murni komponen basi
        (sb / "novelty.py").write_text(t.replace("import config_old as C", "import config as C", 1), encoding="utf-8")
    ops["d. modul dependensi diganti versi arsip (novelty.py)"] = basi

    def lanjut(sb):
        """Run dilanjutkan sesudah konfigurasi berubah: bench_v4 menulis ulang meta.json dengan konfigurasi baru
        walaupun 0 tugas baru dijalankan (lihat blok meta di bench_v4.py)."""
        _cfg(sb, *KANDIDAT_A["BENCH_V4 alpha"])
        kode = "import sys,json; sys.path.insert(0,'.'); import config as C; print(json.dumps(C.BENCH_V4, default=str))"
        baru = json.loads(subprocess.run([sys.executable, "-c", kode], cwd=sb, capture_output=True, text=True).stdout)
        f = sb / "hasil/benchmark_v4/meta.json"; m = json.loads(f.read_text(encoding="utf-8"))
        m.update(konfigurasi=baru, tugas_baru=0); f.write_text(json.dumps(m, indent=1, default=str), encoding="utf-8")
    ops["e. run dilanjutkan sesudah konfigurasi berubah (meta ditulis ulang)"] = lanjut
    return ops


CEK_R = r"""
import importlib.util, json, os, sys
sys.path.insert(0, os.getcwd())
spek = importlib.util.spec_from_file_location('kanon', os.path.join(os.getcwd(), 'config.py'))
K = importlib.util.module_from_spec(spek); spek.loader.exec_module(K)
import importlib
isi = lambda m: json.dumps({k: getattr(m, k, None) for k in ('BENCH', 'BENCH_V4', 'NOVELTY', 'BASELINE', 'TIER', 'SEED')},
                           sort_keys=True, default=str)
alarm = False
for titik, kunci in (('bench_v4', 'BENCH_V4'), ('benchmark', 'BENCH')):     # setiap titik masuk run benchmark
    B = importlib.import_module(titik)
    f = os.path.normcase(os.path.abspath(getattr(B.C, '__file__', '') or ''))
    alarm |= (f != os.path.normcase(os.path.abspath('config.py')) or isi(B.C) != isi(K)
              or json.dumps(B.P, sort_keys=True, default=str) != json.dumps(getattr(K, kunci), sort_keys=True, default=str))
print(json.dumps(bool(alarm)))
"""


def _d5_set(sb):
    """Berkas yang tercatat identik dengan tag v-paper1 di JEJAK_VERSI.md tetapi kini berbeda (logika D5 E8)."""
    blok = (sb / "JEJAK_VERSI.md").read_text(encoding="utf-8").split("## Tag `v-paper1`")[1]
    return {n for n, h, s in re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| (\w+) \|", blok, re.M)
            if s == "identik" and (sb / n).exists() and I.sha_lf(sb / n) != h}


def d5_relatif(sb, ctx):
    """D5 relatif terhadap kontrol: baseline.py dan causal.py sudah sah berbeda dari tag sejak perbaikan E9
    (12-11-2026), sehingga alarm hanya untuk berkas yang berbeda BARU dibanding kontrol."""
    return bool(_d5_set(sb) - ctx["d5_kontrol"])


def d1r(sb, _):
    for d in ("v2", "v3"):                                 # modul SOL v2/v3 dimuat sol_dag (diimpor benchmark.py)
        for p in (I.PROYEK / d).glob("*.py"):
            (sb / d).mkdir(exist_ok=True)
            if not (sb / d / p.name).exists():
                shutil.copy2(p, sb / d / p.name)
    out =subprocess.run([sys.executable, "-c", CEK_R], cwd=sb, capture_output=True, text=True)
    return "galat" if out.returncode else json.loads(out.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    import pandas as pd
    DET = dict(I.DETEKTOR); DET["D5 JEJAK_VERSI (L5)"] = d5_relatif; DET["D1r penjaga runtime (usulan)"] = d1r
    sb0 = I.buat_sandbox()
    ctx = dict(manifest=I.manifest(sb0), drift_kontrol=I._drift(sb0), d5_kontrol=_d5_set(sb0))
    print("D5 kontrol (sudah berbeda dari tag):", sorted(ctx["d5_kontrol"]), flush=True)
    ops = {"kontrol (tanpa kesalahan)": None, **operator(random.Random(BENIH))}
    baris = []
    for nama, f in ops.items():
        sb = I.buat_sandbox() if f else sb0
        if f:
            f(sb)
        r = {"kesalahan": nama, **{d: det(sb, ctx) for d, det in DET.items()}}
        baris.append(r); print(r, flush=True)
        if f:
            shutil.rmtree(sb, ignore_errors=True)
    shutil.rmtree(sb0, ignore_errors=True)
    E = pd.DataFrame(baris)
    E.to_csv(I.ROOT / "tabel" / "E8b_injeksi_eksternal.csv", index=False)
    print(E.set_index("kesalahan").to_string())
