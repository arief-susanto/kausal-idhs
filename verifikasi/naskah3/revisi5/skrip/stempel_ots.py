"""Butir 10 catatan perbaikan (E10): stempel waktu OpenTimestamps (tingkat T5) untuk rencana yang BELUM dijalankan.

  - Naskah 1: protokol evaluasi pengguna, kunci jawaban, formulir SUS, dan skrip analisisnya (data peserta belum ada).
  - Naskah 2: panduan anotasi manusia, bahan rujukan anotator, dan skrip kappa (anotasi belum dikerjakan).
Untuk setiap naskah dibuat manifest berisi SHA-256 (isi berakhiran LF, CRLF dinormalkan, sama dengan verifikasi_kunci.py)
setiap berkas rencana, lalu manifest itu distempel. Hanya hash yang dikirim ke server kalender, bukan isi berkas.
Bukti awal berupa janji kalender; jalankan `upgrade` beberapa jam kemudian untuk memperoleh atestasi blok Bitcoin.

Pakai (dari folder proyek kausal_idhs):
    python naskah/03_reproduksibilitas/skrip/stempel_ots.py --ots "<python venv ots> <ots_jalan.py>" stamp
    python naskah/03_reproduksibilitas/skrip/stempel_ots.py --ots "..." upgrade     # beberapa jam kemudian
    python naskah/03_reproduksibilitas/skrip/stempel_ots.py --ots "..." info
"""
import argparse
import hashlib
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROYEK = ROOT.parents[1]
OUT = ROOT / "tabel" / "E10_opentimestamps"
N1 = Path("naskah_ke_2/01_dsr_sistem_informasi/evaluasi_pengguna")
N2 = Path("naskah_ke_2/02_narasi_otomatis")
RENCANA = {
    "MANIFEST_RENCANA_NASKAH1.txt": [N1 / "PROTOKOL.md", N1 / "analisis_pengguna.py", N1 / "kunci_jawaban.csv",
                                     N1 / "formulir_SUS.md"],
    "MANIFEST_RENCANA_NASKAH2.txt": [N2 / "anotasi/PANDUAN_ANOTASI.md", N2 / "skrip/hitung_kappa.py"]
                                    + sorted((N2 / "anotasi/bahan_rujukan").glob("*.md")),
}


def sha_lf(p):
    return hashlib.sha256((PROYEK / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def tulis_manifest():
    OUT.mkdir(parents=True, exist_ok=True)
    waktu = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for nama, berkas in RENCANA.items():
        f = OUT / nama
        if f.exists():
            raise SystemExit(f"{f.name} sudah ada; manifest yang sudah distempel tidak boleh ditimpa")
        baris = [f"# Manifest rencana (SHA-256 isi berakhiran LF), dibuat {waktu}",
                 "# Verifikasi: hitung SHA-256 tiap berkas sesudah CRLF->LF, bandingkan; lalu `ots verify` berkas .ots"]
        baris += [f"{sha_lf(Path(p).relative_to(PROYEK) if Path(p).is_absolute() else p)} *{Path(p).as_posix()}"
                  for p in berkas]
        f.write_text("\n".join(baris) + "\n", encoding="utf-8", newline="\n")
        print("manifest", f.name, len(berkas), "berkas")


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--ots", required=True); a.add_argument("aksi", choices=["stamp", "upgrade", "info"])
    a = a.parse_args()
    ots = shlex.split(a.ots, posix=False)
    if a.aksi == "stamp":
        tulis_manifest()
        sasaran = [str(OUT / n) for n in RENCANA]
    else:
        sasaran = [str(OUT / f"{n}.ots") for n in RENCANA]
    hasil = subprocess.run(ots + [a.aksi] + sasaran, capture_output=True, text=True)
    print(hasil.stdout, hasil.stderr)
    (OUT / f"log_{a.aksi}.txt").open("a", encoding="utf-8").write(
        f"== {datetime.now(timezone.utc).isoformat()} {a.aksi}\n{hasil.stdout}{hasil.stderr}\n")
