# Catatan deviasi dan pencabutan klaim: SOL-DAG v1 → v2 → v3

Dokumen ini dilampirkan pada disertasi/artikel dan dirujuk dari proposal serta dokumen Tahap 3.
Status: 27-09-2026. Hilir p = 15 selesai; hilir p = 30 (sekunder) masih berjalan.

## 1. Klaim yang dicabut

| Klaim lama (proposal / Tahap 3) | Status | Bukti |
|---|---|---|
| "SD-Hybrid memakai uji independensi bersyarat **baru** yang konsisten desain survei" | **Dicabut** | v3 H8c: keputusan uji t-desain usulan identik dengan uji Wald berpenaksir sandwich terklaster CR1 pada 99,9% pernyataan H0 (heterogen dan homogen). Lemma 2 (TEORI_S10): kedua statistik setara asimtotik (Frisch–Waugh–Lovell); perbedaannya hanya strata dan derajat bebas. |
| "SOL-DAG lebih cepat dan hemat memori daripada baseline" | **Dicabut** | Benchmark v1 (100 replikasi): H2 kecepatan didukung sebagian (3/8); SOL lebih lambat daripada B2, B3, dan N2 di skenario A. H3 memori didukung sebagian (6/8); pada skenario A tidak lebih hemat daripada B2/B3. Keunggulan waktu/memori hanya muncul pada skenario B terhadap metode yang bekerja pada 33 indikator mentah, yaitu efek pengecilan graf oleh MLC, bukan sifat SOL-DAG secara umum. |
| "SOL-DAG lebih akurat daripada baseline" (v1) | **Dicabut** | Benchmark v1 H1 didukung sebagian (6/27): pada skenario A efek T→Y dinolkan pada 97% replikasi (RMSE 0,020 vs 0,009 untuk B1/B2; cakupan CI 3%). |

Usulan redaksi untuk proposal/Tahap 3:
> "Uji independensi bersyarat yang dipakai setara dengan uji Wald berpenaksir sandwich terklaster (CR1) yang sudah dikenal; kontribusi penelitian ini bukan pada statistik ujinya, melainkan pada (i) bukti bahwa koreksi desain yang lazim (Kish, deff global) salah kalibrasi dalam penemuan kausal pada survei kompleks, (ii) penurunan FDR sisi dalam penemuan graf (H7b), meskipun validitas himpunan penyesuaian tidak meningkat (H7a gagal), dan (iii) Proposisi 3 tentang laju konsistensi skeleton yang ditentukan oleh jumlah PSU."

Hapus dari proposal dan Tahap 3: klaim "lebih cepat", "lebih hemat memori", dan "uji baru"; kriteria H2/H3 (kecepatan, memori) sebagai kontribusi SOL-DAG.

## 2. Deviasi v1 → v2 (dari PRAREGISTRASI_v2.md, ditambah deviasi pelaksanaan)

| Komponen | v1 | v2 | Alasan |
|---|---|---|---|
| Estimasi efek | Efek = 0 bila graf tak memuat jalur T→Y | Graf hanya memilih himpunan penyesuaian; efek selalu diestimasi (AIPW, himpunan ala IDA) | Efek nol 97%, cakupan CI 3% |
| Pemisahan sampel | Separuh A menemukan, separuh B mengestimasi | Cross-fitting K = 2 per PSU di dalam strata | Membuang separuh data |
| Koreksi desain | Rao-Scott + α = 0,01 + penalti n_eff + split | Satu koreksi: uji t-desain, α = 0,05, tanpa tahap skor | Tipe I 3,6% (konservatif), daya hilang |
| SE efek | Bootstrap PSU 20 replikasi | Fungsi pengaruh + linearisasi desain | Persentil 20 replikasi tidak stabil |
| Graf acuan | DAG pakar diperturbasi 30% / model MLC | DAG acak patuh tier | Benchmark v1 menguntungkan B1 (A) dan SOL (B) |

Deviasi pelaksanaan v2 (wajib dilaporkan):
1. `run_bench.py` yang diterima berisi 4 sel grid; diubah menjadi 6 sel agar sesuai pra-registrasi (ICC {0,05; 0,4} × β {−0,6; −0,15; 0}) dan ditambah opsi paralel per sel. Seed dan isi sel tidak berubah.
2. Hash kode dicatat pada v2/HASH_KODE_v2.txt; benchmark dijalankan 27-09-2026 pukul 07.29. Tanggal registrasi OSF: ________ (bila setelah 07.29, catat sebagai deviasi).
3. Evaluasi H2v2: versi awal kode evaluasi hanya memeriksa p Wilcoxon; diperbaiki agar mensyaratkan RMSE v2 < v1 **dan** p Holm < 0,05 sesuai teks. Putusan akhir: **gagal** (ICC 0,4: RMSE v2 0,0341 vs v1 0,0307).
4. Evaluasi H3v2: n pernyataan diasumsikan 20 × replikasi per sel (sol_v2 hanya menyimpan proporsi); H3v2–H6v2 digabung antar-sel ICC 0,4 (H5v2 semua sel).

Hasil v2: H1v2, H3v2, H4v2, H5v2, H6v2 diterima; H2v2 gagal.

## 3. Deviasi v2 → v3 (dari PRAREGISTRASI_v3.md, ditambah deviasi pelaksanaan)

- Desain benchmark: sintetis setara IDHS (67 strata × 29 PSU × 9), ICC heterogen U(0,1; 0,8) vs homogen 0,45; kalibrasi deff tingkat-uji ke IDHS nyata (S6 terkonfirmasi: p10/median/p90 = 1,36/2,39/4,41).
- Pembanding: lima uji (naif, Kish, deff-global, sandwich CR1, desain usulan).
- Pengungkapan pilot: 15 replikasi `run_s8.py` dilihat sebelum registrasi; H8c ditambahkan setelah pilot.
- Hash kode: v3/HASH_KODE_v3.txt (27-09-2026 13.11); run dimulai 13.12. Tanggal registrasi OSF: ________.
- Pelaksanaan: `run_downstream.py 100 15` dan `100 30` dijalankan paralel (bukan berurutan); tidak memengaruhi hasil (seed per replikasi).

**Tafsiran skenario H8 dan bagian ambigu (ditetapkan sebelum melihat hasil hilir):**
H8a, H8b, H8d diuji pada skenario heterogen (inti S8); H8c pada gabungan kedua skenario; H7a pada skenario
heterogen seperti tertulis; H7b dan H9 memakai heterogen sebagai skenario utama (homogen dilaporkan); H9 diuji
pada uji desain_usulan dengan p = 15.

Hasil v3 (S8, 200 replikasi × 2 skenario):

| Kode | Hasil | Putusan |
|---|---|---|
| H8a | Tipe I uji desain 5,2% (Wilson 4,7–5,7%) | diterima |
| H8b | Naif 18,2%, Kish 18,4%; deff-global 0,4% | diterima |
| H8c | Kesepakatan dengan CR1 99,9% | diterima → klaim "uji baru" dicabut |
| H8d | Daya desain 54,3% vs deff-global 43,4% (+10,8 pp) | diterima |
| H7a | Validitas penyesuaian: desain 78% vs naif 91%, Kish 86% (p = 15, heterogen) | gagal (arah berlawanan) |
| H7b | FDR sisi: desain 6,2% vs naif 19,3% (heterogen), p Holm 4e-18 | diterima |
| H9 | Cakupan gabungan dan utama 98% (heterogen dan homogen) | diterima |

## 4. Arah berikutnya (bergantung pada H7a/H7b)

- Jika H7a atau H7b diterima: kontribusi "kalibrasi desain survei diperlukan agar penemuan kausal menghasilkan himpunan penyesuaian yang valid", ditambah Proposisi 3.
- Jika keduanya gagal: kebaruan metodologis habis; disertasi dialihkan menjadi studi kausal terapan (pipeline dan temuan sanitasi), dengan hasil kalibrasi sebagai satu bab evaluasi, termasuk hasil negatifnya.

## 5. Riwayat run benchmark semi-sintetik v1 (dirujuk naskah A, Bagian 2.4)

| Run | Waktu | Status | Konfigurasi | Hasil utama skenario A |
|---|---|---|---|---|
| 1a | 27-09-2026, selesai 04:32 (220,5 menit) | selesai, **tidak dilaporkan**; berkas hasil tertimpa run 1b | `benchmark.py` membaca `config_old.py`: α = 0,01; skor BIC diskret; `n_populasi` = 5; penemuan MLC dengan n nominal | menurut log: H1 6/27, H2 3/8, H3 6/8, H4 4/8, H5 0/2 |
| 1b | 27-09-2026, selesai 12:01 (238,4 menit) | selesai, **tidak dilaporkan** | sama dengan run 1a (kesamaan pengaturan persis tidak dapat dipastikan dari berkas yang tersisa) | SOL-DAG v1 efek nol 97%, cakupan 3%; B3 efek nol 23%, cakupan 68%; H1 6/27 (putusan H1–H5 sama dengan run 1a) |
| 2 | 10-10-2026, mulai 14:18 (sebelum audit) | **dihentikan** pada 161 dari 200 tugas (A 100, B 61), tidak dianalisis | sama dengan run 1 | – |
| 3 | 10–11-10-2026 (460,9 menit) | selesai, **dilaporkan** | `config.py` pada commit 74eb7a4 (sesudah audit A1 dan A4; tier `hambatan_biaya` = 2, berbeda dari tag v-paper1 yang memakai tier 3): α = 0,05; skor Gauss; `n_populasi` = 20; 100 replikasi; 20 bootstrap | SOL-DAG v1 efek nol 93%, cakupan 6%; B3 efek nol 35%, cakupan 57%; H1 4/27 |
| 4 | 25-10-2026, selesai 06:02 (253,2 menit) | selesai; **run kanonis** (lihat 5.1) | kode tag v-paper1 (tier `hambatan_biaya` = 3); pengaturan lain sama dengan run 3 | skenario A identik dengan run 3 (selisih hanya pembulatan floating point, < 10⁻⁵); putusan H1–H5 sama (H1 4/27); selisih hanya di skenario B (lihat 5.1) |

Bukti (salinan terlacak git, jejak waktu asli dipertahankan): `naskah_lanjutan/01_efek_nol_graf/bahan/benchmark_v1/riwayat_run/`,
disalin dari `hasil_pra_audit/benchmark/sanitasi_diare/` (run 1b dan 2), `hasil_pra_audit/RINGKASAN.txt` (log run 1a dan 1b),
dan `hasil/benchmark/sanitasi_diare/` (run 3, disalin 18-10-2026; folder itu kini berisi run 4); perbedaan konfigurasi: `git diff 67d1dfb 74eb7a4 -- benchmark.py config.py`.
Angka run 1 di bagian 1 dokumen ini (efek nol 97%, cakupan 3%, H1 6/27) berasal dari run 1b.

### 5.1 Deviasi: tier `hambatan_biaya` dinaikkan ke 3 sesudah run 3

**Yang berubah.** Commit 98841d0 (11-10-2026 11:24:03) menambahkan `TIER.update(hambatan_biaya=3)` di akhir `config.py`,
bersama dua analisis sensitivitas Fase 3 (`sanitasi_diare_ctps` dan `pbi_diare_biaya`). Perubahan ini berlaku global,
termasuk untuk benchmark v1, karena `benchmark.py` membaca tier dari `C.TIER`.

**Urutan waktu.** Run 3 berjalan 10-10-2026 18:36 sampai 11-10-2026 02:17 dengan tier 2. Tier diubah sekitar 9 jam
sesudah run 3 selesai. Tag v-paper1 ("Kode final naskah", 11-10-2026 13:08) memakai tier 3, sehingga angka run 3 tidak
dapat dihasilkan ulang dari kode pada tag naskah.

**Alasan perubahan** (tertulis di komentar kode dan runbook):
1. Analisis sensitivitas `pbi_diare_biaya` memperlakukan hambatan biaya sebagai mediator (PBI/JKN gratis → hambatan
   biaya → diare). Panah T_pbi (tier 3) → `hambatan_biaya` hanya sah bila `hambatan_biaya` berada pada tier ≥ 3.
2. Temuan audit konfigurasi: `hambatan_biaya` (tier 2) dan `hambatan_jarak` (tier 3) berasal dari jenis pertanyaan yang
   sama, sehingga tier keduanya disamakan (komentar AUDIT di `config.py`, usul "keduanya 3").

**Rencana sudah tertulis sebelum run 3.** Berkas `Runbook VS Code Fase 0–5 Perbaikan Kausal IDHS.pdf` ikut dalam
snapshot pra-audit (commit 67d1dfb, tag `pra-audit`, 10-10-2026 16:59, sebelum run 3 dimulai). Langkah 3.1 runbook memuat
blok kode Fase 3 yang sama persis dengan commit 98841d0, termasuk `TIER.update(hambatan_biaya=3)` dan dua baris komentar
alasannya, serta catatan "TIER.update(hambatan_biaya=3) berlaku untuk semua analisis". Komentar AUDIT yang mengusulkan
tier 3 juga sudah ada di `config.py` pada snapshot yang sama. Perintah pemeriksa:
`git grep -c -a "hambatan_biaya=3" 67d1dfb` dan `git show v-paper1:config.py | grep -n hambatan_biaya`.

**Letak deviasinya.** Runbook hanya meminta baseline `pbi_diare` dijalankan ulang sesudah perubahan tier. Benchmark v1
tidak dijalankan ulang sebelum tag v-paper1 dibuat, padahal runbook langkah 4 menetapkan bahwa setiap angka naskah harus
dapat ditelusuri ke satu commit. Akibatnya angka benchmark v1 yang dilaporkan (run 3) berasal dari commit 74eb7a4, bukan
dari tag naskah. Rencana dan alasan perubahan tertulis sebelum run 3 dimulai, tetapi perubahan dilaksanakan sesudah hasil
run 3 tersedia. Penulis menyatakan bahwa hasil run 3 sudah dilihat sebelum perubahan tier dilaksanakan; repositori
hanya membuktikan bahwa rencana tertulis lebih dulu, sehingga perubahan ini dicatat sebagai deviasi.

**Dampak (run 4, kode tag v-paper1).** Skenario A identik dengan run 3 untuk semua metode (selisih hanya pembulatan
floating point, < 10⁻⁵), dan putusan H1–H5 sama. Skenario B berbeda pada metode yang memakai tier indikator mentah:
B3 indikator mentah (SID 85,5 → 95,0; SHD 14,34 → 14,36), N3 tanpa konstruk (SHD 28,14 → 28,20; SID 82,57 → 82,29;
cakupan 0,84 → 0,85), B2 indikator mentah (SID 69,85 → 69,90), dan SOL tanpa MLC (stabilitas SHD 4,18 → 4,20; jumlah
sisi 18,09 → 18,11). SOL-DAG dan N3 MLC-DAG tidak berubah selain pembulatan.

**Uji penentu.** Skenario B penuh (100 replikasi) dijalankan ulang dengan kode sekarang dan tier 2
(`naskah_ke_2/03_reproduksibilitas/skrip/ulang_run3_tier2.py`, luaran `naskah_ke_2/03_reproduksibilitas/tabel/E5_run3_tier2/`).
Hasil (01-11-2026, 305 menit): 60 dari 60 nilai ringkasan (6 metode × 10 metrik) identik dengan run 3 (selisih maksimum 2,1 × 10⁻¹⁷, setara pembulatan floating point), dan RD benar skenario B sama persis. Terhadap run 4 hanya 33 dari 60 yang identik (selisih maksimum 9,5, yaitu SID B3 indikator mentah). Jadi perubahan tier menjelaskan seluruh selisih run 3 vs run 4, termasuk SID 9,5.

**Run kanonis.** Run 4 ditetapkan sebagai run kanonis karena dihasilkan dari kode tag v-paper1. Angka skenario A yang
dikutip naskah tidak berubah; run 3 tetap disimpan sebagai bukti riwayat.

### 5.2 Pemisahan efek konfigurasi basi dan efek perubahan kode (run 1b → run 3)

Benchmark v1 dijalankan ulang (01-11-2026, 289 menit, skenario A dan B, 100 replikasi) dengan **kode sekarang** dan
**seluruh 12 nilai `config_old.py`** yang berbeda (7 di antaranya dibaca benchmark: α di tiga tempat, fungsi skor di tiga
tempat, `n_populasi`), tier `hambatan_biaya` = 2. Skrip `naskah_ke_2/03_reproduksibilitas/skrip/ulang_config_lama.py`,
luaran `naskah_ke_2/03_reproduksibilitas/tabel/E4_config_lama/`. Selisih terhadap run 1b = efek perubahan kode sejak
27-09-2026 (termasuk A4–A6, tidak hanya itu); selisih terhadap run 3 = efek konfigurasi basi.

| Metrik | Run 1b (config_old, kode lama) | Config_old + kode sekarang | Run 3 (config benar, kode sekarang) |
|---|---|---|---|
| A, SOL-DAG efek nol / cakupan | 97% / 3% | 91% / 8% | 93% / 6% |
| A, N1 SD-Hybrid efek nol / cakupan | 98% / 1% | 79% / 18% | 77% / 19% |
| A, B3 BN skor efek nol / cakupan | 23% / 68% | 23% / 68% | 35% / 57% |
| B, SOL tanpa MLC efek nol | 68% | 63% | 24% |
| B, SOL-DAG efek nol / cakupan | 26% / 62% | 15% / 73% | 10% / 75% |

Temuan:
- Metode baseline skenario A (B1, B2, B3) identik dengan run 1b pada 30 dari 30 nilai ringkasan. Kode sekarang dengan
  `config_old` menghasilkan ulang run 1b persis untuk metode yang tidak tersentuh audit, sehingga run 1b memang memakai
  `config_old`, dan perubahan B3 (efek nol 23% → 35%) seluruhnya berasal dari konfigurasi.
- Metode novelty skenario A (N1, N2, varian SOL) berubah terutama karena kode: N1 efek nol 98% → 79%, SOL-DAG 97% → 91%;
  perubahan konfigurasi menambah sedikit (SOL-DAG 91% → 93%).
- Penurunan efek nol SOL tanpa MLC di skenario B sebesar 44 poin persen (68% → 24%) sebagian besar berasal dari
  konfigurasi (63% → 24%, 39 poin) dan sebagian kecil dari kode (68% → 63%, 5 poin). Di dalam konfigurasi, efeknya
  gabungan tujuh parameter dan tidak dapat diatribusikan ke satu parameter dengan rancangan ini.
- Putusan H1–H5 run gabungan sama dengan run 1b (H5 "tidak didukung"), sehingga perubahan H5 menjadi "didukung sebagian" pada run 3 berasal dari konfigurasi. Batasnya tipis: galat tipe I uji terkoreksi 3,6% (IK 95% 2,9–4,6%) dengan konfigurasi basi dan 4,5% (3,6–5,4%) dengan konfigurasi benar, terhadap target 5% (`putusan_config_lama.py`; H2 dan H3 bergantung pada waktu komputasi).
- Tidak ada metode yang identik di kedua acuan; terhadap run 1b 39 dari 150 nilai identik, terhadap run 3 22 dari 150.

## 6. Kunci rencana simulasi perluasan naskah A (celah jejak waktu)

Rencana simulasi perluasan (`naskah_lanjutan/01_efek_nol_graf/RENCANA_ANALISIS.md`) dan skripnya dikunci dengan hash
SHA-256 dalam berkas teks, bukan dengan commit git sebelum run:
- Kunci rencana awal: `tabel/perluasan/KUNCI_RENCANA.txt`, waktu 2026-10-18 09:43:15 +0700; run penuh dimulai setelahnya.
- Kunci replikasi: `tabel/replikasi/KUNCI_REPLIKASI.txt`, waktu 2026-10-18 16:48:37 +0700, setelah bagian "Tambahan"
  (aturan pelaporan replikasi) ditulis dan sebelum run replikasi; run pertama sudah dilihat pada saat itu.
- Rencana, skrip, dan hasil baru di-commit pada e068ba9 setelah kedua run selesai. Bagian "Tambahan" ditambahkan ke
  berkas rencana yang sama sebelum commit, sehingga versi rencana awal tidak tersimpan sebagai commit tersendiri.

Yang dapat diverifikasi: isi rencana awal direkonstruksi sebagai `RENCANA_ANALISIS_v1_terkunci.md` dan hash-nya sama
dengan kunci 09:43; skrip simulasi tidak berubah sejak dikunci; semua seed tetap sehingga hasil dapat diulang persis.
Jalankan `python skrip/verifikasi_kunci.py` dari folder `naskah_lanjutan/01_efek_nol_graf`.
Yang tidak dapat diverifikasi lewat git: bahwa waktu kunci (jejak waktu sistem berkas) mendahului pembacaan hasil.
Tindakan ke depan: rencana di-commit sebelum run penuh dan, bila memungkinkan, didaftarkan ke OSF atau diarsipkan ke
Zenodo untuk stempel waktu pihak ketiga.
