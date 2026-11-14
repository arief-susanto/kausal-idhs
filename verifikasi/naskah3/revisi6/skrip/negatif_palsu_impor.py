"""E7b negatif palsu pemeriksa impor (review 14-11-2026, M1c dan M2).

Setiap varian menyuntikkan konfigurasi basi ke benchmark.py dengan cara impor yang berbeda, pada salinan terisolasi
berkas .py di akar proyek. Untuk setiap varian dijalankan tiga detektor:
  D1  pemeriksa impor AST (periksa_impor_config.py, E7)                       -- statis
  IL  Import Linter, kontrak forbidden: paket tidak boleh mengimpor config_old,
      config_audit, config_sebelum_audit (skrip dibungkus ke satu paket karena
      Import Linter hanya menerima paket; modul konfigurasi diperlakukan eksternal) -- statis
  D1r penjaga runtime: benchmark diimpor, lalu modul konfigurasi yang benar-benar dipakainya (benchmark.C)
      dibandingkan dengan config.py kanonis (jalur berkas dan isi BENCH/BASELINE/NOVELTY/TIER)  -- dinamis
Kebenaran dasar: parameter efektif yang dibaca benchmark (benchmark.P dan benchmark.C) berbeda dari kanonis.

Pakai (dari folder proyek kausal_idhs):
    python -m pip install -r requirements-verifikasi.txt     # sekali: Import Linter 2.16
    python naskah/03_reproduksibilitas/skrip/negatif_palsu_impor.py [--lint-imports <jalur lain>]
Bawaan: lint-imports di folder Scripts/bin lingkungan Python yang menjalankan skrip ini; bila tidak ada, skrip berhenti.
Keluaran: naskah/03_reproduksibilitas/tabel/E7b_negatif_palsu_impor.csv
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKRIP = Path(__file__).resolve().parent
ROOT = SKRIP.parent
PROYEK = ROOT.parents[1]
sys.path.insert(0, str(SKRIP))
from periksa_impor_config import berkas_kerja, periksa  # noqa: E402

ASLI = "import config as C   # AUDIT A1: sebelumnya config_old"
DIR = 'os.path.dirname(os.path.abspath(__file__))'


def ganti(sb, lama, baru, berkas="benchmark.py"):
    f = sb / berkas; t = f.read_text(encoding="utf-8"); assert lama in t, lama
    f.write_text(t.replace(lama, baru, 1), encoding="utf-8")


def v_literal(sb): ganti(sb, ASLI, "import config_old as C")
def v_bintang(sb): ganti(sb, ASLI, "import sys\nfrom config_old import *  # noqa\nC = sys.modules['config_old']")
def v_importlib_literal(sb): ganti(sb, ASLI, "import importlib\nC = importlib.import_module('config_old')")
def v_importlib_var(sb): ganti(sb, ASLI, "import importlib\nNAMA_CFG = os.environ.get('CFG', 'config_old')\n"
                                         "C = importlib.import_module(NAMA_CFG)")
def v_dunder_gabung(sb): ganti(sb, ASLI, "C = __import__('config' + '_old')")
def v_perantara_akar(sb):
    (sb / "pengaturan.py").write_text("from config_old import *  # noqa\n", encoding="utf-8")
    ganti(sb, ASLI, "import pengaturan as C")
def v_perantara_subfolder(sb):
    (sb / "util").mkdir(); (sb / "util/__init__.py").write_text("", encoding="utf-8")
    (sb / "util/pengaturan.py").write_text("from config_old import *  # noqa\n", encoding="utf-8")
    ganti(sb, ASLI, "from util import pengaturan as C")
def v_sys_path(sb):
    (sb / "arsip").mkdir()                                # salinan arsip; ROOT tetap akar proyek agar run tetap senyap
    (sb / "arsip/config.py").write_text((sb / "config_old.py").read_text(encoding="utf-8").replace(
        "ROOT = Path(__file__).parent", "ROOT = Path(__file__).parent.parent", 1), encoding="utf-8")
    ganti(sb, ASLI, f"import sys\nsys.path.insert(0, os.path.join({DIR}, 'arsip'))\nimport config as C")
def v_exec(sb):
    ganti(sb, ASLI, "import types\nC = types.ModuleType('config')\n"
                    f"C.__file__ = os.path.join({DIR}, 'config_old.py')\n"
                    "exec(open(C.__file__, encoding='utf-8').read(), C.__dict__)")
def v_nama_tak_berpola(sb):
    shutil.copy2(sb / "config_old.py", sb / "pengaturan_lama.py")
    ganti(sb, ASLI, "import pengaturan_lama as C")
def v_json(sb):
    import importlib.util
    spek = importlib.util.spec_from_file_location("cfg_lama", sb / "config_old.py"); m = importlib.util.module_from_spec(spek)
    spek.loader.exec_module(m)
    (sb / "params_bench.json").write_text(json.dumps(m.BENCH, default=str), encoding="utf-8")
    ganti(sb, "P = C.BENCH", f"P = json.load(open(os.path.join({DIR}, 'params_bench.json'), encoding='utf-8'))")


VARIAN = {"V0 kontrol (tanpa kesalahan)": None,
          "V1 import literal (kejadian nyata)": v_literal,
          "V2 from ... import *": v_bintang,
          "V3 importlib, argumen literal": v_importlib_literal,
          "V4 importlib, argumen variabel": v_importlib_var,
          "V5 __import__ dengan string gabungan": v_dunder_gabung,
          "V6 re-export lewat modul perantara di akar": v_perantara_akar,
          "V7 re-export lewat modul perantara di subfolder": v_perantara_subfolder,
          "V8 manipulasi sys.path (config.py lain)": v_sys_path,
          "V9 exec atas berkas konfigurasi lama": v_exec,
          "V10 konfigurasi lama bernama tak berpola": v_nama_tak_berpola,
          "V11 parameter dibaca dari JSON berjalur salah": v_json}

CEK = r"""
import importlib.util, json, os, sys
sys.path.insert(0, os.getcwd())
spek = importlib.util.spec_from_file_location('kanon', os.path.join(os.getcwd(), 'config.py'))
K = importlib.util.module_from_spec(spek); spek.loader.exec_module(K)
import benchmark as B
isi = lambda m: json.dumps({k: getattr(m, k, None) for k in ('BENCH', 'BASELINE', 'NOVELTY', 'TIER')}, sort_keys=True, default=str)
f = os.path.normcase(os.path.abspath(getattr(B.C, '__file__', '') or ''))
d1r = f != os.path.normcase(os.path.abspath('config.py')) or isi(B.C) != isi(K)
efektif = isi(B.C) != isi(K) or json.dumps(B.P, sort_keys=True, default=str) != json.dumps(K.BENCH, sort_keys=True, default=str)
print(json.dumps(dict(d1r=bool(d1r), benar_basi=bool(efektif))))
"""

KONTRAK = """[importlinter]
root_package = pipa
include_external_packages = True

[importlinter:contract:satu-config]
name = Satu modul konfigurasi
type = forbidden
source_modules = pipa
forbidden_modules =
    config_old
    config_audit
    config_sebelum_audit
allow_indirect_imports = False
"""


def import_linter(sb, exe):
    w = Path(tempfile.mkdtemp(prefix="il_")); (w / "pipa").mkdir()
    for p in sb.glob("*.py"):
        if not p.name.startswith("config") and not p.name.endswith("_sebelum_audit.py"):   # arsip dinyatakan, setara D1
            shutil.copy2(p, w / "pipa" / p.name)
    (w / "pipa/__init__.py").write_text("", encoding="utf-8"); (w / ".importlinter").write_text(KONTRAK, encoding="utf-8")
    out = subprocess.run([exe], cwd=w, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env=dict(os.environ, PYTHONPATH=str(w), PYTHONIOENCODING="utf-8"))
    shutil.rmtree(w, ignore_errors=True)
    if "Broken contracts" in out.stdout:
        return True
    assert "Contracts: 1 kept" in out.stdout or "1 kept" in out.stdout, out.stdout[-500:] + out.stderr[-500:]
    return False


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--lint-imports"); a = a.parse_args()
    if not a.lint_imports:
        a.lint_imports = shutil.which("lint-imports", path=str(Path(sys.executable).parent)) or shutil.which("lint-imports")
    if not a.lint_imports:
        sys.exit("lint-imports tidak ditemukan: pasang dengan  python -m pip install -r requirements-verifikasi.txt")
    print("Import Linter:", a.lint_imports, flush=True)
    import pandas as pd
    baris = []
    for nama, f in VARIAN.items():
        sb = Path(tempfile.mkdtemp(prefix="e7b_"))
        for p in PROYEK.glob("*.py"):
            shutil.copy2(p, sb / p.name)
        for d in ("v2", "v3"):                                # modul SOL v2/v3 yang dimuat sol_dag lewat C.ROOT
            for p in (PROYEK / d).glob("*.py"):
                (sb / d).mkdir(exist_ok=True); shutil.copy2(p, sb / d / p.name)
        if f:
            f(sb)
        out = subprocess.run([sys.executable, "-c", CEK], cwd=sb, capture_output=True, text=True,
                             env=dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8"))
        assert out.returncode == 0, (nama, out.stderr[-1500:])
        r = json.loads(out.stdout.strip().splitlines()[-1])
        r = {"varian": nama, "konfigurasi efektif basi": r["benar_basi"],
             "D1 pemeriksa impor": bool(periksa(berkas_kerja(sb), "config", ["*_sebelum_audit.py"])[1]),
             "IL Import Linter": import_linter(sb, a.lint_imports),
             "D1r penjaga runtime": r["d1r"]}
        baris.append(r); print(r, flush=True)
        shutil.rmtree(sb, ignore_errors=True)
    E = pd.DataFrame(baris)
    assert not E.iloc[0, 1:].any(), "kontrol harus bersih"
    assert E.iloc[1:]["konfigurasi efektif basi"].all(), "setiap varian harus benar-benar basi"
    E.to_csv(ROOT / "tabel" / "E7b_negatif_palsu_impor.csv", index=False)
    print(E.set_index("varian").to_string())
