"""E8 injeksi kesalahan terkendali (butir 4 catatan perbaikan; mirip mutation testing).

Setiap kesalahan disuntikkan ke SALINAN TERISOLASI proyek (sandbox baru per kesalahan; proyek asli tidak disentuh),
lalu semua detektor dijalankan. Kontrol = sandbox tanpa kesalahan (harus bersih: tidak ada alarm palsu).

Kesalahan (Fx):
  F1 impor basi            : benchmark.py mengimpor config_old, bukan config (disuntik sesudah rilis tercatat)
  F1b impor basi sebelum rilis: sama, tetapi hash JEJAK_VERSI ikut mencatat versi basi (seperti kejadian nyata)
  F2 benih hilang          : bench_v4.satu() memakai default_rng() tanpa benih
  F3 salinan beku ditimpa  : salinan beku diganti isi hasil aktif terbaru (pembekuan ulang tak sengaja)
  F4 salinan beku diubah   : satu angka salinan beku diubah manual
  F5 konfigurasi berubah   : BENCH_V4["alpha"] diubah sesudah run, tanpa menjalankan ulang
  F6 rencana terkunci diubah: skrip simulasi naskah A diubah sesudah hash dikunci
  F7 kode analisis berubah : causal.py diubah sesudah tag naskah (v-paper1)
  F8 folder salinan beku dipindah: naskah/data dipindah (kejadian nyata 11-2026); naskah_bahan.py memakai
     cadangan `H = BEKU if BEKU.exists() else C.OUT` sehingga diam-diam membaca luaran aktif
Detektor (Dx, lapis):
  D1 pemeriksa impor (L1+E7) | D2 kunci rencana (L2) | D3 reproduksi satu tugas thd hasil tersimpan (L3)
  D4 drift beku vs aktif (L4, cara E3) | D4m manifest hash salinan beku di jalur yang dibaca skrip (L4 usulan)
  D5 JEJAK_VERSI (L5) | D6 konfigurasi di meta.json run (provenans run)
  L6 (catatan deviasi) bersifat manual dan tidak diuji di sini.
Sandbox meniru susunan yang dirujuk skrip naskah (salinan beku di naskah/data).

Pakai (dari folder proyek kausal_idhs):  python naskah/03_reproduksibilitas/skrip/injeksi_kesalahan.py [--tanpa-d3]
Keluaran: naskah/03_reproduksibilitas/tabel/E8_injeksi_kesalahan.csv
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKRIP = Path(__file__).resolve().parent
ROOT = SKRIP.parent
PROYEK = ROOT.parents[1]
PUBLIK = PROYEK.parent / "kausal-idhs-publik"
sys.path.insert(0, str(SKRIP))
from periksa_impor_config import berkas_kerja, periksa  # noqa: E402

BEKU_SUMBER = Path("naskah/01 Resti/data")                # lokasi salinan beku di proyek sekarang
BEKU_REL = Path("naskah/data")                            # jalur yang dirujuk naskah_bahan.py / naskah_bekukan.py
NA = Path("naskah_lanjutan/01_efek_nol_graf")
TUGAS_D3 = ("icc=0.15|beta=0.0|lemah|p=15", 0)          # satu tugas benchmark v4 yang hasilnya tersimpan
KUNCI_L2 = {NA / "tabel/perluasan/KUNCI_RENCANA.txt": [("RENCANA_ANALISIS.md", NA / "RENCANA_ANALISIS_v1_terkunci.md"),
                                                     ("skrip/sim_perluasan.py", NA / "skrip/sim_perluasan.py")],
            NA / "tabel/replikasi/KUNCI_REPLIKASI.txt": [("RENCANA_ANALISIS.md", NA / "RENCANA_ANALISIS.md"),
                                                        ("skrip/sim_replikasi.py", NA / "skrip/sim_replikasi.py"),
                                                        ("skrip/sim_perluasan.py", NA / "skrip/sim_perluasan.py")]}


def sha_lf(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ------------------------------------------------------------------ sandbox
def buat_sandbox():
    sb = Path(tempfile.mkdtemp(prefix="injeksi_", dir=os.environ.get("SANDBOX_INJEKSI")))
    for p in PROYEK.glob("*.py"):
        shutil.copy2(p, sb / p.name)
    for p in PROYEK.glob("RENCANA*.md"):
        shutil.copy2(p, sb / p.name)
    shutil.copytree(PROYEK / BEKU_SUMBER, sb / BEKU_REL)
    rel_beku = [p.relative_to(PROYEK / BEKU_SUMBER) for p in (PROYEK / BEKU_SUMBER).rglob("*") if p.is_file()]
    for r in rel_beku:                                    # hanya luaran aktif yang punya salinan beku
        q = PROYEK / "hasil" / r
        if q.exists():
            (sb / "hasil" / r).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(q, sb / "hasil" / r)
    for kunci, peta in KUNCI_L2.items():
        for p in [kunci] + [b for _, b in peta]:
            (sb / p).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(PROYEK / p, sb / p)
    shutil.copy2(PUBLIK / "JEJAK_VERSI.md", sb / "JEJAK_VERSI.md")
    return sb


def manifest(sb):
    """Manifest hash salinan beku (usulan L4: dicatat saat pembekuan, diperiksa di jalur yang dibaca skrip naskah)."""
    akar = sb / BEKU_REL
    if not akar.exists():
        return {}
    return {str(p.relative_to(akar)).replace("\\", "/"): sha_lf(p) for p in sorted(akar.rglob("*")) if p.is_file()}


# ------------------------------------------------------------------ kesalahan
def ganti(path, lama, baru):
    t = path.read_text(encoding="utf-8")
    assert lama in t, (path.name, lama[:50])
    path.write_text(t.replace(lama, baru, 1), encoding="utf-8")


def f1(sb): ganti(sb / "benchmark.py", "import config as C", "import config_old as C")
def f1b(sb):
    """Kejadian nyata: impor basi sudah ada SEBELUM rilis, sehingga hash di JEJAK_VERSI ikut mencatat versi basi."""
    f1(sb)
    j = sb / "JEJAK_VERSI.md"; t = j.read_text(encoding="utf-8")
    t = re.sub(r"(\| `benchmark\.py` \| `)[0-9a-f]{64}(` \|)", lambda m: m.group(1) + sha_lf(sb / "benchmark.py") + m.group(2), t)
    j.write_text(t, encoding="utf-8")


def f2(sb): ganti(sb / "bench_v4.py", "rng = np.random.default_rng([C.SEED, r, zlib.crc32(sel_id(s).encode())])",
                  "rng = np.random.default_rng()")
def f3(sb):
    rel = Path("kausal/pbi_diare/estimasi.csv")
    shutil.copy2(sb / "hasil" / rel, sb / BEKU_REL / rel)
def f4(sb):
    f = sb / BEKU_REL / "idhs_m0m6/sanitasi_diare/rd.csv"
    t = f.read_text(encoding="utf-8"); m = re.search(r"-0\.0\d{3}", t)
    f.write_text(t[:m.start()] + m.group(0)[:-1] + str((int(m.group(0)[-1]) + 1) % 10) + t[m.end():], encoding="utf-8")
def f5(sb): ganti(sb / "config.py", "alpha=0.05,                     # alpha uji untuk M2/M3",
                  "alpha=0.01,                     # alpha uji untuk M2/M3")
def f6(sb):
    f = sb / NA / "skrip/sim_perluasan.py"; f.write_text(f.read_text(encoding="utf-8") + "\n# diubah sesudah dikunci\n", encoding="utf-8")
def f7(sb):
    f = sb / "causal.py"; f.write_text(f.read_text(encoding="utf-8").replace("quantile(.975)", "quantile(.97)", 1), encoding="utf-8")
def f8(sb):
    (sb / BEKU_SUMBER).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(sb / BEKU_REL), str(sb / BEKU_SUMBER))


KESALAHAN = {"F0 kontrol (tanpa kesalahan)": None, "F1 impor basi sesudah rilis": f1,
             "F1b impor basi sebelum rilis (kejadian nyata)": f1b, "F2 benih hilang": f2,
             "F3 salinan beku ditimpa isi aktif": f3, "F4 salinan beku diubah manual": f4,
             "F5 konfigurasi diubah sesudah run": f5, "F6 rencana terkunci diubah": f6,
             "F7 kode analisis diubah sesudah tag": f7, "F8 folder salinan beku dipindah": f8}


# ------------------------------------------------------------------ detektor (True = alarm)
def d1(sb, _):
    return bool(periksa(berkas_kerja(sb), "config", ["*_sebelum_audit.py"])[1])


def d2(sb, _):
    gagal = 0
    for kunci, peta in KUNCI_L2.items():
        tercatat = {n: h for h, n in re.findall(r"^([0-9a-f]{64}) \*(.+)$", (sb / kunci).read_text(encoding="utf-8"), re.M)}
        gagal += sum(tercatat.get(n) != sha_lf(sb / b) for n, b in peta)
    return gagal > 0


def d3(sb, _):
    """Jalankan satu tugas bench_v4 di sandbox (utas BLAS = 1) dan bandingkan dengan baris tersimpan."""
    kode = ("import os,sys,json; [os.environ.__setitem__(v,'1') for v in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')];"
            "sys.path.insert(0,'.'); import warnings; warnings.filterwarnings('ignore'); import bench_v4 as B;"
            f"s=[x for x in B.sel_list() if B.sel_id(x)=={TUGAS_D3[0]!r}][0];"
            f"print(json.dumps(B.satu((s,{TUGAS_D3[1]})),default=str))")
    env = dict(os.environ, PYTHONPATH="")
    out = subprocess.run([sys.executable, "-c", kode], cwd=sb, capture_output=True, text=True, env=env)
    if out.returncode:
        return "galat"                                     # galat eksekusi = kesalahan bersuara
    import pandas as pd
    baru = pd.DataFrame(json.loads(out.stdout.strip().splitlines()[-1]))
    asli = pd.read_csv(PROYEK / "hasil/benchmark_v4/per_rep.csv", low_memory=False, float_precision="round_trip")
    asli = asli[(asli.sel == TUGAS_D3[0]) & (asli.rep == TUGAS_D3[1])]
    m = baru.merge(asli, on=["sel", "rep", "metode"], suffixes=("_b", "_a"))
    if len(m) != len(asli):
        return True
    for k in ("RD_hat", "se", "RD_lo", "RD_hi", "FDR", "recall"):
        if ((m[f"{k}_b"] - m[f"{k}_a"]).abs() > 1e-12).any():
            return True
    return any((m[f"{k}_b"].astype(str) != m[f"{k}_a"].astype(str)).any() for k in ("n_Z", "Z", "valid", "cakup"))


def _drift(sb):
    akar = sb / BEKU_REL
    return {str(p.relative_to(akar)) for p in akar.rglob("*") if p.is_file() and (sb / "hasil" / p.relative_to(akar)).exists()
            and sha_lf(p) != sha_lf(sb / "hasil" / p.relative_to(akar))}


def d4(sb, ctx):                                           # alarm bila ada drift BARU dibanding kontrol
    return bool(_drift(sb) - ctx["drift_kontrol"])


def d4m(sb, ctx):
    return manifest(sb) != ctx["manifest"]


def d5(sb, _):
    teks = (sb / "JEJAK_VERSI.md").read_text(encoding="utf-8")
    blok = teks.split("## Tag `v-paper1`")[1]
    beda = 0
    for nama, h, status in re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| (\w+) \|", blok, re.M):
        p = sb / nama
        if status == "identik" and p.exists():             # hanya berkas yang tercatat identik dengan rilis
            beda += sha_lf(p) != h
    return beda > 0


def d6(sb, _):
    meta = json.loads((sb / "hasil/benchmark_v4/meta.json").read_text(encoding="utf-8"))["konfigurasi"]
    kode = "import sys,json; sys.path.insert(0,'.'); import config as C; print(json.dumps(C.BENCH_V4, default=str))"
    out = subprocess.run([sys.executable, "-c", kode], cwd=sb, capture_output=True, text=True)
    if out.returncode:
        return "galat"
    sekarang = json.loads(out.stdout)
    return any(json.dumps(sekarang.get(k), default=str) != json.dumps(v, default=str) for k, v in meta.items() if k in sekarang)


DETEKTOR = {"D1 pemeriksa impor (L1+E7)": d1, "D2 kunci rencana (L2)": d2, "D3 reproduksi tugas tersimpan (L3)": d3,
            "D4 drift beku vs aktif (L4, E3)": d4, "D4m manifest salinan beku (L4 usulan)": d4m,
            "D5 JEJAK_VERSI (L5)": d5, "D6 konfigurasi di meta run": d6}


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--tanpa-d3", action="store_true"); a = a.parse_args()
    if a.tanpa_d3:
        DETEKTOR.pop("D3 reproduksi tugas tersimpan (L3)")
    import pandas as pd
    sb0 = buat_sandbox()
    ctx = dict(manifest=manifest(sb0), drift_kontrol=_drift(sb0))
    baris = []
    for nama_f, fungsi in KESALAHAN.items():
        sb = buat_sandbox() if fungsi else sb0
        if fungsi:
            fungsi(sb)
        r = {"kesalahan": nama_f}
        for nama_d, det in DETEKTOR.items():
            r[nama_d] = det(sb, ctx)
        baris.append(r); print(r, flush=True)
        if fungsi:
            shutil.rmtree(sb, ignore_errors=True)
    shutil.rmtree(sb0, ignore_errors=True)
    E8 = pd.DataFrame(baris)
    E8.to_csv(ROOT / "tabel" / "E8_injeksi_kesalahan.csv", index=False)
    print(E8.set_index("kesalahan").to_string())
