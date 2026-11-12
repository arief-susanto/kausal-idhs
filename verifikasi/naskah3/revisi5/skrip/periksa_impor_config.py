"""Pemeriksa impor konfigurasi berbasis AST (rekomendasi 1 naskah 3; butir 1 catatan perbaikan, evaluasi E7).

Aturan: semua modul pipeline (berkas .py di akar repositori) harus mengimpor SATU modul konfigurasi yang sama,
yaitu modul kanonis (bawaan: config). Modul konfigurasi = nama yang cocok dengan ^config(_\\w+)?$.
Impor dikenali dari node Import/ImportFrom di mana pun (termasuk di dalam fungsi) dan dari
importlib.import_module("...") / __import__("...") dengan argumen string literal.
Berkas arsip yang sengaja tidak dijalankan dapat dinyatakan dengan pola --arsip (mis. *_sebelum_audit.py).

Mode:
  python periksa_impor_config.py                    # pohon kerja saat ini; kode keluar 1 bila melanggar (gerbang)
  python periksa_impor_config.py --riwayat OUT.csv  # jalankan mundur pada setiap commit git (E7)
"""
import argparse
import ast
import csv
import fnmatch
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

POLA_CONFIG = re.compile(r"^config(_\w+)?$")
ARSIP_BAWAAN = ["*_sebelum_audit.py"]


def impor_config(sumber):
    """Kembalikan himpunan nama modul konfigurasi yang diimpor oleh satu sumber Python."""
    try:
        pohon = ast.parse(sumber)
    except SyntaxError:
        return {"<sintaks-galat>"}
    nama = set()
    for n in ast.walk(pohon):
        if isinstance(n, ast.Import):
            nama |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            nama.add(n.module.split(".")[0])
        elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            f = n.func
            fn = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fn in ("import_module", "__import__"):
                nama.add(n.args[0].value.split(".")[0])
    return {m for m in nama if POLA_CONFIG.match(m)}


def periksa(berkas, kanonis="config", arsip=()):
    """berkas: {jalur: sumber}. Kembalikan (pemakaian Counter, daftar pelanggaran (jalur, modul))."""
    pakai, langgar = Counter(), []
    for jalur, src in sorted(berkas.items()):
        if any(fnmatch.fnmatch(Path(jalur).name, p) for p in arsip):
            continue
        for m in sorted(impor_config(src)):
            pakai[m] += 1
            if m != kanonis:
                langgar.append((jalur, m))
    return pakai, langgar


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, check=True).stdout.decode("utf-8", "replace")


def berkas_commit(c):
    nama = [p for p in _git("ls-tree", "--name-only", c).splitlines() if p.endswith(".py")]
    return {p: _git("show", f"{c}:{p}") for p in nama}


def berkas_kerja(akar):
    return {p.name: p.read_text(encoding="utf-8", errors="replace") for p in Path(akar).glob("*.py")}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--kanonis", default="config")
    a.add_argument("--arsip", nargs="*", default=ARSIP_BAWAAN)
    a.add_argument("--akar", default=".")
    a.add_argument("--riwayat", help="tulis hasil per commit ke CSV ini")
    a = a.parse_args()
    if a.riwayat:
        baris = []
        for rec in _git("log", "--all", "--reverse", "--date=iso", "--format=%h|%ad|%s").splitlines():
            c, tgl, judul = rec.split("|", 2)
            b = berkas_commit(c)
            p0, l0 = periksa(b, a.kanonis, arsip=())
            p1, l1 = periksa(b, a.kanonis, arsip=a.arsip)
            baris.append(dict(commit=c, tanggal=tgl, judul=judul, berkas_py=len(b),
                              modul_config=";".join(f"{m}:{n}" for m, n in sorted(p0.items())),
                              langgar_mentah=len(l0), langgar_sesudah_arsip=len(l1),
                              berkas_langgar=";".join(sorted({j for j, _ in l1})),
                              berkas_arsip=";".join(sorted({j for j, _ in l0} - {j for j, _ in l1}))))
        with open(a.riwayat, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(baris[0])); w.writeheader(); w.writerows(baris)
        for r in baris:
            print(r["commit"], r["tanggal"][:16], "mentah", r["langgar_mentah"], "| sesudah arsip",
                  r["langgar_sesudah_arsip"], "|", r["modul_config"])
        sys.exit(0)
    pakai, langgar = periksa(berkas_kerja(a.akar), a.kanonis, a.arsip)
    print("modul konfigurasi:", dict(pakai))
    for j, m in langgar:
        print(f"MELANGGAR: {j} mengimpor {m} (kanonis: {a.kanonis})")
    sys.exit(1 if langgar else 0)
