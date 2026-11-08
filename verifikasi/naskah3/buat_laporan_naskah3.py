"""Susun LAPORAN_VERIFIKASI_NASKAH3 (.md dan .docx): pemeriksaan N3-1 sampai N3-4 untuk naskah 3 (§6.4 dan §6.5).

  N3-1  tier hambatan_biaya di tag naskah (menentukan run kanonis)
  N3-2  alasan dan waktu perubahan tier (deviasi), serta analisis yang dijalankan dengan tier 3
  N3-3  pemisahan efek konfigurasi basi dari efek perbaikan kode (run gabungan: kode sekarang + config_old)
  N3-4  uji penentu §6.5: skenario B penuh dengan tier 2, dibanding run 3 (ringkasan) dan run 4 (per replikasi)

Kode pemeriksaan ini berbeda dari kode audit A1-A6 (laporan terpisah di dok_disertasi/verifikasi_audit/).
Bukti git dibaca langsung saat skrip dijalankan; angka run dibaca dari luaran skrip berikut (folder naskah_ke_2/03_reproduksibilitas):
  skrip/ulang_config_lama.py, skrip/putusan_config_lama.py  -> tabel/E4_config_lama/
  skrip/ulang_run3_tier2.py                                   -> tabel/E5_run3_tier2/
Pakai (dari folder proyek kausal_idhs):  python dok_disertasi/verifikasi_naskah3/buat_laporan_naskah3.py
"""
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt

S = Path(__file__).resolve().parent
PROYEK = S.parents[1]
N3 = PROYEK / "naskah_ke_2/03_reproduksibilitas"
T4, T5 = N3 / "tabel/E4_config_lama", N3 / "tabel/E5_run3_tier2"
RIW = PROYEK / "naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run"
RUN4 = PROYEK / "hasil/benchmark/sanitasi_diare"
TAG, KOMIT_TIER, KOMIT_ULANG, KOMIT_RUN3, PRA = "v-paper1", "98841d0", "4806252", "74eb7a4", "67d1dfb"
RUNBOOK = "Runbook VS Code Fase 0–5 Perbaikan Kausal IDHS.pdf"


def git(*a, biner=False):
    r = subprocess.run(["git", *a], cwd=PROYEK, capture_output=True, check=True)
    return r.stdout if biner else r.stdout.decode("utf-8", "replace").strip()


sha = lambda b: hashlib.sha256(b).hexdigest()
rp = lambda x, d=1: f"{x:,.{d}f}".replace(",", "#").replace(".", ",").replace("#", ".")
waktu_berkas = lambda f: dt.datetime.fromtimestamp(Path(f).stat().st_mtime).strftime("%Y-%m-%d %H:%M")
blok = []
add = lambda j, x: blok.append((j, x))

# ------------------------------------------------------------------ kepala
HEAD = git("rev-parse", "HEAD"); kotor = bool(git("status", "--porcelain", "--", "config.py", "benchmark.py"))
# SHA-256 atas isi dengan akhir baris LF (git menyimpan LF; direktori kerja Windows memakai CRLF karena core.autocrlf)
lf = lambda b: b.replace(b"\r\n", b"\n")
cfg_kerja = sha(lf((PROYEK / "config.py").read_bytes()))
cfg_tag = sha(git("show", f"{TAG}:config.py", biner=True))
cfg_run3 = sha(git("show", f"{KOMIT_RUN3}:config.py", biner=True))
bm_kerja, bm_tag = sha(lf((PROYEK / "benchmark.py").read_bytes())), sha(git("show", f"{TAG}:benchmark.py", biner=True))
blob_sama = {n: git("hash-object", n) == git("rev-parse", f"{TAG}:{n}") for n in ("config.py", "benchmark.py")}
m4 = json.loads((T4 / "meta.json").read_text(encoding="utf-8")); m5 = json.loads((T5 / "meta.json").read_text(encoding="utf-8"))

add("h1", "Laporan Verifikasi Naskah 3: Pemeriksaan N3-1 sampai N3-4")
add("p", f"Waktu laporan disusun: {dt.datetime.now():%Y-%m-%d %H:%M}. HEAD: {HEAD}"
         f"{' (config.py/benchmark.py berubah dari HEAD)' if kotor else ''}.")
add("t", pd.DataFrame([
    ["config.py (direktori kerja)", cfg_kerja[:16], "dipakai run N3-3 dan N3-4 (lalu ditambal di memori)"],
    [f"config.py pada tag {TAG}", cfg_tag[:16], "identik dengan direktori kerja (blob git sama)" if cfg_tag == cfg_kerja and blob_sama["config.py"] else "BERBEDA dari direktori kerja"],
    [f"config.py pada {KOMIT_RUN3} (kode run 3)", cfg_run3[:16], "berbeda dari tag hanya pada blok Fase 3 (lihat N3-1)"],
    ["benchmark.py (direktori kerja)", bm_kerja[:16], "identik dengan tag (blob git sama)" if bm_kerja == bm_tag and blob_sama["benchmark.py"] else "BERBEDA dari tag"],
], columns=["Berkas", "SHA-256 (16 digit awal)", "Keterangan"]))
add("t", pd.DataFrame([
    ["N3-3 run gabungan", "A dan B", f"{m4['rep']} per skenario (200 tugas)", waktu_berkas(T4 / "per_rep_config_lama.csv"),
     f"{m4['menit']} menit, {m4['pekerja']} pekerja"],
    ["N3-4 skenario B tier 2", "B", f"{m5['rep']} (100 tugas)", waktu_berkas(T5 / "per_rep_B_tier2.csv"),
     f"{m5['menit']} menit, {m5['pekerja']} pekerja"],
    ["Run 1b (acuan)", "A dan B", "100 per skenario", "2026-09-27 12:01", "config_old, kode sebelum audit"],
    ["Run 3 (acuan, dilaporkan)", "A dan B", "100 per skenario", "2026-10-11 02:17", f"commit {KOMIT_RUN3}, tier 2"],
    ["Run 4 (acuan)", "A dan B", "100 per skenario", waktu_berkas(RUN4 / "per_rep.csv"), f"kode tag {TAG}, tier 3"],
], columns=["Run", "Skenario", "Replikasi", "Selesai", "Keterangan"]))
add("p", "Seluruh run memakai benih per tugas default_rng([SEED, replikasi, skenario]), satu utas BLAS, dan cache data "
         "analisis yang sama. Mikrodata tidak disertakan dalam laporan ini.")

# ------------------------------------------------------------------ N3-1
add("h2", "N3-1. Tier hambatan_biaya di tag naskah")
tag_info = git("log", "-1", "--format=%H %ci", TAG); tag_pesan = git("tag", "-l", "-n1", TAG)
baris_tag = [b for b in git("show", f"{TAG}:config.py").splitlines() if "hambatan_biaya" in b and ("TIER" in b or "fromkeys" in b)]
n_tag = [i + 1 for i, b in enumerate(git("show", f"{TAG}:config.py").splitlines()) if "TIER.update(hambatan_biaya" in b]
tier_ev = []
for ref in (PRA, KOMIT_RUN3, KOMIT_TIER, TAG):
    teks = git("show", f"{ref}:config.py")
    t = 3 if "TIER.update(hambatan_biaya=3)" in teks else 2
    tier_ev.append([ref, git("log", "-1", "--format=%ci", ref)[:16], t])
add("p", f"Perintah: git tag -l -n; git show {TAG}:config.py | grep -n hambatan_biaya; git log -1 --format='%H %ci' {TAG}.")
add("li", f"Tag: {tag_pesan}; commit {tag_info}.")
add("li", f"config.py pada tag memasang hambatan_biaya di tier 2 dalam definisi TIER, lalu menimpanya di baris {n_tag[0]}: "
          f"TIER.update(hambatan_biaya=3). Tier efektif di tag naskah: 3.")
add("t", pd.DataFrame(tier_ev, columns=["Commit/tag", "Waktu", "Tier efektif hambatan_biaya"]))
ds = git("diff", "--stat", KOMIT_RUN3, TAG, "--", "config.py", "benchmark.py", "baseline.py", "novelty.py", "sol_dag.py")
hapus = sum(1 for x in git("diff", KOMIT_RUN3, TAG, "--", "config.py").splitlines() if x.startswith("-") and not x.startswith("---"))
add("li", f"git diff --stat {KOMIT_RUN3} {TAG} -- config.py benchmark.py baseline.py novelty.py sol_dag.py: "
          f"{' '.join(ds.split())}; baris dihapus di config.py: {hapus}. Jadi kode run 3 dan kode tag hanya berbeda pada "
          f"blok Fase 3 yang ditambahkan di akhir config.py (dua analisis sensitivitas dan TIER.update(hambatan_biaya=3)).")
add("p", f"Kesimpulan: tag naskah memakai tier 3, sedangkan run 3 (yang dilaporkan) berjalan dengan tier 2 pada commit "
         f"{KOMIT_RUN3}. Angka run 3 tidak dapat dihasilkan dari kode tag. Run 4 (kode tag) ditetapkan sebagai run kanonis.")

# ------------------------------------------------------------------ N3-2
add("h2", "N3-2. Alasan dan waktu perubahan tier (deviasi)")
stat = git("show", KOMIT_TIER, "--stat", "--format=%H %ci %s")
diff = git("show", KOMIT_TIER, "--format=", "--", "config.py")
alasan = [b.lstrip("+# ").strip() for b in diff.splitlines() if b.startswith("+#") and ("tier" in b.lower())]
import shutil, tempfile  # noqa: E401,E402
n_runbook = "tidak dihitung (pdftotext tidak tersedia)"
if shutil.which("pdftotext"):
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "runbook.pdf"; pdf.write_bytes(git("show", f"{PRA}:{RUNBOOK}", biner=True))
        teks_rb = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    n_runbook = teks_rb.count("hambatan_biaya=3")
_baris = git("show", f"{PRA}:config.py").splitlines()
audit_pra = []
for i, b in enumerate(_baris):                                  # blok komentar AUDIT yang menyebut hambatan_biaya
    if b.strip().startswith("# AUDIT") and "hambatan_biaya" in b:
        isi = [b.strip("# ").strip()]
        for c in _baris[i + 1:]:
            if not c.strip().startswith("#") or c.strip().startswith("# AUDIT"):
                break
            isi.append(c.strip("# ").strip())
        audit_pra.append(" ".join(isi))
add("p", f"Perintah: git show {KOMIT_TIER} --stat; git show {KOMIT_TIER} -- config.py.")
add("li", "Commit perubahan: " + stat.splitlines()[0])
add("li", "Berkas dalam commit: " + "; ".join(b.strip() for b in stat.splitlines()[1:] if "|" in b))
add("li", "Alasan yang tertulis di kode: " + " ".join(alasan))
add("h2", "Urutan waktu")
add("t", pd.DataFrame([
    ["2026-10-10 16:59", f"Snapshot pra-audit ({PRA}). Komentar AUDIT di config.py mengusulkan tier 3; runbook Fase 0–5 "
                         f"langkah 3.1 memuat baris TIER.update(hambatan_biaya=3) beserta alasannya ({n_runbook} kemunculan di PDF)."],
    ["2026-10-10 18:36", "Run 3 benchmark v1 dimulai (tier 2)"],
    ["2026-10-11 02:17", "Run 3 selesai"],
    ["2026-10-11 ±11:02–11:23", "Run Fase 3 IDHS (log_fase3.txt): baseline, inferensi kausal, dan SOL v2 dengan tier 3"],
    ["2026-10-11 11:24", f"Commit {KOMIT_TIER}: TIER.update(hambatan_biaya=3) dan dua analisis sensitivitas"],
    ["2026-10-11 13:00", f"Commit {KOMIT_ULANG}: hasil ulang sesudah perubahan tier (log_fase3_ulang_tier.txt) dan M0–M6 IDHS"],
    ["2026-10-11 13:08", f"Tag {TAG} (tier 3)"],
    ["2026-10-25 06:02", "Run 4 benchmark v1 selesai (kode tag, tier 3)"],
], columns=["Waktu", "Kejadian"]))
add("p", "Komentar AUDIT di snapshot pra-audit: " + " / ".join(audit_pra))
add("p", "Apakah keputusan diambil sesudah melihat hasil run 3: rencana dan alasan perubahan sudah tertulis sebelum run 3 "
         "dimulai (runbook dan komentar AUDIT pada snapshot pra-audit), dan isi commit 98841d0 sama dengan blok di runbook. "
         "Pelaksanaannya terjadi sekitar 9 jam sesudah run 3 selesai. Pernyataan penulis: hasil run 3 sudah dilihat sebelum "
         "perubahan tier dilaksanakan; perubahan itu mengikuti langkah 3.1 runbook yang tertulis sebelum run 3 dimulai. "
         "Repositori hanya dapat membuktikan bahwa rencana tertulis lebih dulu, tidak dapat membuktikan bahwa keputusan "
         "pelaksanaan tidak dipengaruhi hasil run 3. Karena itu perubahan ini diperlakukan sebagai deviasi.")
add("p", "Letak deviasi: runbook hanya meminta baseline pbi_diare dijalankan ulang sesudah perubahan tier; benchmark v1 "
         "tidak dijalankan ulang sebelum tag dibuat, padahal runbook langkah 4 menetapkan bahwa setiap angka naskah harus "
         "dapat ditelusuri ke satu commit.")

# analisis dengan tier 3
import sys  # noqa: E402
sys.path.insert(0, str(PROYEK))
import config as C  # noqa: E402
pakai = {k: ("hambatan_biaya" in str(v)) for k, v in C.ANALISIS.items()}
lf3, lul = git("show", f"{KOMIT_TIER}:log_fase3.txt"), git("show", f"{KOMIT_ULANG}:log_fase3_ulang_tier.txt")
jalan = lambda log: sorted({f"{m.group(1)} {m.group(2)}" for m in re.finditer(r"\[(baseline|kausal|sol_v2|N1|N2) ([a-z_]+) exit 0", log)})
add("h2", "Analisis yang dijalankan dengan tier 3")
rows = []
for nama, ada in pakai.items():
    di_f3 = [j.split()[0] for j in jalan(lf3) if j.split()[1] == nama]
    di_ul = [j.split()[0] for j in jalan(lul) if j.split()[1] == nama]
    rows.append([nama, "ya" if ada else "tidak", ", ".join(di_f3) or "–", ", ".join(di_ul) or "–"])
rows.append(["sanitasi_diare tanpa trimming", "tidak", "kausal", "–"])
add("t", pd.DataFrame(rows, columns=["Analisis IDHS", "DAG memuat hambatan_biaya", f"Dijalankan di log_fase3 (sebelum {KOMIT_TIER})",
                                     f"Dijalankan ulang di {KOMIT_ULANG}"]))
add("li", "M0–M6 pada IDHS (sanitasi_diare, pbi_diare): commit 4806252, tier 3. Seluruh menu aplikasi dijalankan ulang "
          "11-10 16:10–17:36 dan 25-10 dengan tier 3 (penyelarasan; lihat drift E3).")
add("li", "Benchmark v4 (simulasi utama, selesai 11-10 10:24) tidak membaca C.TIER: DGP-nya membangkitkan tier sintetis "
          "sendiri, jadi tidak terpengaruh perubahan ini.")
add("li", "Benchmark v1: run 3 (tier 2, dilaporkan) dan run 4 (tier 3).")
# bukti bahwa log_fase3 memakai tier 3: struktur baseline pbi_diare
rx = lambda log: (re.search(r"BASE\[pbi_diare\] B2 uji=(\d+).*?SHD vs pakar=(\d+)", log).groups(),
                  re.search(r"BASE\[pbi_diare\] B3 skor=\w+ langkah=(\d+).*?SHD vs pakar=(\d+)", log).groups())
t2 = rx(git("show", "a02d204:log_baseline_pbi_diare.txt")); t3 = rx(lf3)
beku = pd.read_csv(PROYEK / "naskah/data/baseline/pbi_diare/rangkuman.csv").set_index("kode")
add("p", "Bukti bahwa run log_fase3 (sebelum commit 11:24) sudah memakai tier 3, dari baseline pbi_diare yang membaca tier:")
add("t", pd.DataFrame([
    ["log_baseline_pbi_diare.txt (Fase 1, 10-10, tier 2)", t2[0][0], t2[0][1], t2[1][0], t2[1][1]],
    ["log_fase3.txt (11-10, sebelum 11:24)", t3[0][0], t3[0][1], t3[1][0], t3[1][1]],
    ["naskah/data (salinan beku naskah)", "–", int(beku.loc["B2", "SHD"]), int(beku.loc["B3", "sisi"]), int(beku.loc["B3", "SHD"])],
], columns=["Sumber", "B2 jumlah uji", "B2 SHD vs pakar", "B3 langkah/sisi", "B3 SHD vs pakar"]))

# ------------------------------------------------------------------ N3-3
add("h2", "N3-3. Pemisahan efek konfigurasi basi dari efek perbaikan kode")
cfg = pd.read_csv(T4 / "config_lama_dipasang.csv")
add("p", f"Run gabungan: kode sekarang (sesudah audit A1–A6), tier hambatan_biaya = {m4['tier']}, dan seluruh "
         f"{len(cfg)} nilai config_old yang berbeda dari config.py; {int(cfg.dibaca_benchmark.sum())} di antaranya dibaca "
         f"benchmark v1. Nilai yang tidak dibaca tidak memengaruhi hasil, tetapi ikut dipasang agar run ini setara dengan "
         f"\"konfigurasi basi + kode sekarang\".")
add("t", cfg.assign(dibaca_benchmark=cfg.dibaca_benchmark.map({True: "ya", False: "tidak"})))
baca = lambda f: pd.read_csv(f, float_precision="round_trip").set_index(["skenario", "metode"])
r1, rg, r3 = baca(RIW / "run1_2026-09-27/ringkasan.csv"), baca(T4 / "ringkasan_config_lama.csv"), baca(RIW / "run3_2026-10-10_11_dilaporkan/ringkasan.csv")
en = pd.DataFrame(dict(run1b=r1.efek_nol, gabungan=rg.efek_nol, run3=r3.efek_nol))
en["efek_kode_pp"] = (en.gabungan - en.run1b) * 100; en["efek_konfig_pp"] = (en.run3 - en.gabungan) * 100
en["total_pp"] = (en.run3 - en.run1b) * 100
en["paling_dekat"] = np.where((en.gabungan - en.run1b).abs() < (en.gabungan - en.run3).abs(), "run 1b",
                              np.where((en.gabungan - en.run1b).abs() > (en.gabungan - en.run3).abs(), "run 3", "sama"))
en.to_csv(S / "N3-3_dekomposisi_efek_nol.csv")
tb = en.reset_index()
for k in ("run1b", "gabungan", "run3"):
    tb[k] = (tb[k] * 100).round(0).astype(int).astype(str) + "%"
for k in ("efek_kode_pp", "efek_konfig_pp", "total_pp"):
    tb[k] = tb[k].round(0).astype(int)
add("p", f"Proporsi replikasi dengan efek dinihilkan per metode (100 replikasi per sel). Efek kode = gabungan − run 1b; "
         f"efek konfigurasi = run 3 − gabungan.")
add("t", tb.rename(columns={"run1b": "Run 1b", "gabungan": "Gabungan", "run3": "Run 3", "efek_kode_pp": "Efek kode (pp)",
                            "efek_konfig_pp": "Efek konfigurasi (pp)", "total_pp": "Total (pp)", "paling_dekat": "Gabungan paling dekat ke"}))
B = pd.read_csv(T4 / "banding_run3_run1b.csv"); B["id"] = B.selisih <= 1e-12
bas = B[(B.acuan == "run1b") & (B.skenario == "A") & B.metode.str.match(r"B[123] ")]
pg = pd.read_csv(T4 / "putusan.csv").set_index("hipotesis")
p1 = pd.read_csv(RIW / "run1_2026-09-27/putusan.csv").set_index("hipotesis")
p3 = pd.read_csv(RIW / "run3_2026-10-10_11_dilaporkan/putusan.csv").set_index("hipotesis")
put = pd.DataFrame({"Run 1b": p1.putusan + " (" + p1.SOL_lebih_baik.astype(str) + "/" + p1.perbandingan.astype(str) + ")",
                    "Gabungan": pg.putusan + " (" + pg.SOL_lebih_baik.astype(str) + "/" + pg.perbandingan.astype(str) + ")",
                    "Run 3": p3.putusan + " (" + p3.SOL_lebih_baik.astype(str) + "/" + p3.perbandingan.astype(str) + ")"})
h5g, h53 = pd.read_csv(T4 / "hipotesis_H5.csv"), pd.read_csv(RUN4 / "hipotesis_H5.csv")
t1 = lambda h, u: h[(h.ukuran == "galat tipe I") & (h.uji == u)].iloc[0]
ik = lambda r: f"{rp(100 * r.nilai)}% [{rp(100 * r.ci_lo)}–{rp(100 * r.ci_hi)}]"
add("li", f"Validasi titik antara: metode baseline skenario A (B1–B3), yang tidak tersentuh perbaikan kode, identik "
          f"dengan run 1b pada {int(bas.id.sum())} dari {len(bas)} nilai ringkasan (toleransi 10⁻¹²). Jadi run 1b memang "
          f"memakai config_old, dan run gabungan sah sebagai titik antara.")
add("li", "Skenario A, metode novelty (N1, N2, SOL tanpa pemisahan sampel): pergeseran 21 pp hampir seluruhnya efek kode "
          "(19–21 pp); konfigurasi menyumbang 0–2 pp. Hasil gabungan dekat ke run 3, sehingga klaim lama §6.4 (seluruh "
          "pergeseran akibat konfigurasi basi) harus diubah.")
add("li", "Skenario A, B3: pergeseran 12 pp seluruhnya efek konfigurasi.")
add("li", "Skenario B, SOL tanpa MLC: pergeseran 44 pp terdiri atas 39 pp efek konfigurasi dan 5 pp efek kode.")
add("li", "Efek konfigurasi adalah efek gabungan tujuh parameter yang berubah bersamaan; rancangan ini tidak "
          "mengatribusikannya ke satu parameter.")
add("p", "Putusan H1–H5 (100 replikasi per skenario; uji Wilcoxon dengan koreksi Holm, H5 dari 2.000 pernyataan uji):")
add("t", put.reset_index().rename(columns={"hipotesis": "Hipotesis"}))
add("p", f"Putusan run gabungan sama dengan run 1b pada kelima hipotesis, sehingga perubahan H5 berasal dari konfigurasi. "
         f"Galat tipe I uji terkoreksi (target 5%, IK Wilson 95%): {ik(t1(h5g, 'terkoreksi'))} dengan konfigurasi basi dan "
         f"{ik(t1(h53, 'terkoreksi'))} dengan konfigurasi benar; uji naif {ik(t1(h5g, 'naif'))} dan {ik(t1(h53, 'naif'))}. "
         f"H2 dan H3 bergantung pada waktu komputasi dan tidak dapat dibandingkan antar-run.")
rk4 = pd.DataFrame(m4["ringkas"])
add("p", "Kesamaan seluruh nilai ringkasan (15 metode × 10 metrik = 150 nilai): " +
    "; ".join(f"terhadap {r.acuan}: {r.identik_1e12}/{r.sel} identik, selisih maksimum {rp(r.selisih_maks, 2)}" for r in rk4.itertuples()) + ".")

# ------------------------------------------------------------------ N3-4
add("h2", "N3-4. Uji penentu §6.5: skenario B penuh dengan tier 2")
rk5 = {r["acuan"]: r for r in m5["ringkas"]}
add("p", f"Kode sekarang, config.py sekarang, kecuali tier hambatan_biaya = {m5['tier']}; skenario B, {m5['rep']} replikasi. "
         f"RD benar skenario B: {m5['RD_benar_B']} (run 3: {m5['RD_benar_B_run3']}; "
         f"{'identik' if m5['RD_benar_B'] == m5['RD_benar_B_run3'] else 'BERBEDA'}).")
add("t", pd.DataFrame([
    ["Run 3 (tier 2)", "ringkasan (6 metode × 10 metrik)", f"{rk5['run3']['identik_1e12']}/{rk5['run3']['sel']}",
     f"{rk5['run3']['selisih_maks']:.1e}"],
    ["Run 4 (tier 3)", "ringkasan (6 metode × 10 metrik)", f"{rk5['run4']['identik_1e12']}/{rk5['run4']['sel']}",
     rp(rk5['run4']['selisih_maks'], 2)],
], columns=["Acuan", "Tingkat", "Identik (≤10⁻¹²)", "Selisih maksimum"]))
add("catatan", "Luaran per replikasi run 3 tidak tersimpan: per_rep.csv di hasil/benchmark ditimpa run 4, dan salinan "
               "riwayat run 3 hanya memuat ringkasan. Karena itu perbandingan per replikasi dilakukan terhadap run 4; "
               "perbandingan terhadap run 3 dilakukan pada tingkat ringkasan.")
a = pd.read_csv(T5 / "per_rep_B_tier2.csv", float_precision="round_trip")
b = pd.read_csv(RUN4 / "per_rep.csv", float_precision="round_trip"); b = b[b.skenario == "B"]
m = a.merge(b, on=["skenario", "metode", "rep"], suffixes=("_t2", "_4"))
K = ["RD_hat", "RD_lo", "RD_hi", "SHD", "SID", "langkah", "sisi"]
sama = lambda x, y: (x == y) | (x.isna() & y.isna())
m["identik"] = np.logical_and.reduce([sama(m[k + "_t2"], m[k + "_4"]) for k in K])
rows = []
for mt, g in m.groupby("metode", sort=False):
    dS, dI = (g.SHD_t2 - g.SHD_4).abs(), (g.SID_t2 - g.SID_4).abs()
    rows.append([mt, f"{int(g.identik.sum())}/{len(g)}", int(dS.max()), rp(dS.mean(), 2),
                 "–" if dI.isna().all() else int(dI.max()), "–" if dI.isna().all() else rp(dI.mean(), 2),
                 f"{int(g.SID_t2.notna().sum())} / {int(g.SID_4.notna().sum())}",
                 int((g.SID_t2.isna() != g.SID_4.isna()).sum()), f"{(g.RD_hat_t2 - g.RD_hat_4).abs().max():.1e}"])
per = pd.DataFrame(rows, columns=["Metode", "Replikasi identik", "|ΔSHD| maks", "|ΔSHD| rata-rata", "|ΔSID| maks",
                                  "|ΔSID| rata-rata", "SID terdefinisi (tier 2 / run 4)", "Status SID berubah", "|ΔRD| maks"])
per.to_csv(S / "N3-4_per_replikasi_vs_run4.csv", index=False)
add("p", f"Perbandingan per replikasi tier 2 vs run 4 (kolom RD, batas IK, SHD, SID, langkah, sisi; {len(m)} pasangan "
         f"metode-replikasi). Identik bit demi bit: {int(m.identik.sum())} dari {len(m)}. |ΔSID| dihitung pada replikasi "
         f"yang SID-nya terdefinisi di kedua run.")
add("t", per)
add("p", "Menjelaskan SID 9,5 vs \"hingga 1 per replikasi\": untuk B3 indikator mentah, SID hanya terdefinisi pada 2 dari 100 "
         "replikasi di run tier 2 (rata-rata 85,5) dan 1 dari 100 di run 4 (95,0). Selisih rata-rata 9,5 muncul karena satu "
         "replikasi berpindah dari terdefinisi menjadi tidak terdefinisi, bukan karena SID per replikasi berubah 9,5; pada "
         "replikasi yang terdefinisi di kedua run selisihnya 0. Rata-rata SID metode ini berbasis 1–2 replikasi dan sebaiknya "
         "dilaporkan bersama jumlah replikasi yang terdefinisi.")
add("p", "Kesimpulan N3-4: dengan tier 2, kode sekarang menghasilkan ulang run 3 pada seluruh nilai ringkasan; perubahan tier "
         "menjelaskan seluruh selisih run 3 vs run 4, termasuk SID 9,5.")

# ------------------------------------------------------------------ dampak
add("h2", "Dampak pada naskah 3")
add("li", "§6.4: pergeseran 21 pp skenario A dipisah menjadi efek kode (19 pp) dan konfigurasi (2 pp); efek konfigurasi "
          "disebut efek gabungan; perubahan H5 diatribusikan ke konfigurasi dengan catatan batas tipis.")
add("li", "§6.5: hasil N3-4, deviasi tier (N3-2), run 4 sebagai run kanonis (N3-1); SID B3 indikator mentah dilaporkan "
          "bersama jumlah replikasi yang terdefinisi.")
add("li", "Catatan deviasi: CATATAN_DEVIASI.md bagian 5.1 dan 5.2.")


# ------------------------------------------------------------------ keluaran
def md_tabel(df):
    df = df.astype(str)
    return "\n".join(["| " + " | ".join(df.columns) + " |", "|" + "---|" * df.shape[1]]
                     + ["| " + " | ".join(r) + " |" for r in df.values])


MD = {"h1": "# {}", "h2": "## {}", "p": "{}", "li": "- {}", "catatan": "> Catatan: {}", "catatan_kuning": "> **{}**"}
md = [md_tabel(x) if j == "t" else MD[j].format(x) for j, x in blok]
(S / "LAPORAN_VERIFIKASI_NASKAH3.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
for j, x in blok:
    if j == "h1":
        d.add_heading(x, 0)
    elif j == "h2":
        d.add_heading(x, 1)
    elif j == "p":
        d.add_paragraph(x)
    elif j == "li":
        d.add_paragraph(x, style="List Bullet")
    elif j == "catatan":
        r = d.add_paragraph().add_run("Catatan: " + x); r.italic = True
    elif j == "catatan_kuning":
        r = d.add_paragraph().add_run(x); r.bold = True; r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    elif j == "t":
        tb_ = d.add_table(rows=1, cols=x.shape[1]); tb_.style = "Light Grid Accent 1"
        for c, n in zip(tb_.rows[0].cells, x.columns):
            c.text = str(n)
        for row in x.astype(str).values:
            for c, v in zip(tb_.add_row().cells, row):
                c.text = v
        for row in tb_.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(8.5)
        d.add_paragraph()
out = S / "LAPORAN_VERIFIKASI_NASKAH3.docx"
try:
    d.save(out)
except PermissionError:
    out = out.with_name(out.stem + "_baru.docx"); d.save(out)
print("Tersimpan:", out, "dan LAPORAN_VERIFIKASI_NASKAH3.md")
