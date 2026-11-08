# Laporan Verifikasi Naskah 3: Pemeriksaan N3-1 sampai N3-4

Waktu laporan disusun: 2026-11-08 15:38. HEAD: b857c001f9d09c240021ac7bd1d5ebfa1d1344b1.

| Berkas | SHA-256 (16 digit awal) | Keterangan |
|---|---|---|
| config.py (direktori kerja) | d6c2fd7ba1524c07 | dipakai run N3-3 dan N3-4 (lalu ditambal di memori) |
| config.py pada tag v-paper1 | d6c2fd7ba1524c07 | identik dengan direktori kerja (blob git sama) |
| config.py pada 74eb7a4 (kode run 3) | 2b6bb27c05986512 | berbeda dari tag hanya pada blok Fase 3 (lihat N3-1) |
| benchmark.py (direktori kerja) | 62f0659e6aeabbd1 | identik dengan tag (blob git sama) |

| Run | Skenario | Replikasi | Selesai | Keterangan |
|---|---|---|---|---|
| N3-3 run gabungan | A dan B | 100 per skenario (200 tugas) | 2026-11-01 15:44 | 289.0 menit, 4 pekerja |
| N3-4 skenario B tier 2 | B | 100 (100 tugas) | 2026-11-01 14:29 | 305.4 menit, 4 pekerja |
| Run 1b (acuan) | A dan B | 100 per skenario | 2026-09-27 12:01 | config_old, kode sebelum audit |
| Run 3 (acuan, dilaporkan) | A dan B | 100 per skenario | 2026-10-11 02:17 | commit 74eb7a4, tier 2 |
| Run 4 (acuan) | A dan B | 100 per skenario | 2026-10-25 06:02 | kode tag v-paper1, tier 3 |

Seluruh run memakai benih per tugas default_rng([SEED, replikasi, skenario]), satu utas BLAS, dan cache data analisis yang sama. Mikrodata tidak disertakan dalam laporan ini.

## N3-1. Tier hambatan_biaya di tag naskah

Perintah: git tag -l -n; git show v-paper1:config.py | grep -n hambatan_biaya; git log -1 --format='%H %ci' v-paper1.

- Tag: v-paper1        Kode final naskah; commit b077acea04f12382a0cb1d18b0fe4026dd5fe611 2026-10-11 13:08:13 +0700.

- config.py pada tag memasang hambatan_biaya di tier 2 dalam definisi TIER, lalu menimpanya di baris 250: TIER.update(hambatan_biaya=3). Tier efektif di tag naskah: 3.

| Commit/tag | Waktu | Tier efektif hambatan_biaya |
|---|---|---|
| 67d1dfb | 2026-10-10 16:59 | 2 |
| 74eb7a4 | 2026-10-10 17:00 | 2 |
| 98841d0 | 2026-10-11 11:24 | 3 |
| v-paper1 | 2026-10-11 13:08 | 3 |

- git diff --stat 74eb7a4 v-paper1 -- config.py benchmark.py baseline.py novelty.py sol_dag.py: config.py | 16 ++++++++++++++++ 1 file changed, 16 insertions(+); baris dihapus di config.py: 0. Jadi kode run 3 dan kode tag hanya berbeda pada blok Fase 3 yang ditambahkan di akhir config.py (dua analisis sensitivitas dan TIER.update(hambatan_biaya=3)).

Kesimpulan: tag naskah memakai tier 3, sedangkan run 3 (yang dilaporkan) berjalan dengan tier 2 pada commit 74eb7a4. Angka run 3 tidak dapat dihasilkan dari kode tag. Run 4 (kode tag) ditetapkan sebagai run kanonis.

## N3-2. Alasan dan waktu perubahan tier (deviasi)

Perintah: git show 98841d0 --stat; git show 98841d0 -- config.py.

- Commit perubahan: 98841d0f5fe590f60ea5918a436f6c9b6881de6d 2026-10-11 11:24:03 +0700 Fase 3: analisis sensitivitas mediator, tier hambatan_biaya=3, hasil IDHS

- Berkas dalam commit: config.py              | 16 ++++++++++++++; log_fase3.txt          | 58 ++++++++++++++++++++++++++++++++++++++++++++++++++; ringkasan/fase3_rd.csv | 40 ++++++++++++++++++++++++++++++++++

- Alasan yang tertulis di kode: Panah T_pbi (tier 3) -> hambatan_biaya hanya sah bila tier hambatan >= 3. Ini juga menyamakan tier hambatan_biaya dengan hambatan_jarak (temuan audit config).

## Urutan waktu

| Waktu | Kejadian |
|---|---|
| 2026-10-10 16:59 | Snapshot pra-audit (67d1dfb). Komentar AUDIT di config.py mengusulkan tier 3; runbook Fase 0–5 langkah 3.1 memuat baris TIER.update(hambatan_biaya=3) beserta alasannya (2 kemunculan di PDF). |
| 2026-10-10 18:36 | Run 3 benchmark v1 dimulai (tier 2) |
| 2026-10-11 02:17 | Run 3 selesai |
| 2026-10-11 ±11:02–11:23 | Run Fase 3 IDHS (log_fase3.txt): baseline, inferensi kausal, dan SOL v2 dengan tier 3 |
| 2026-10-11 11:24 | Commit 98841d0: TIER.update(hambatan_biaya=3) dan dua analisis sensitivitas |
| 2026-10-11 13:00 | Commit 4806252: hasil ulang sesudah perubahan tier (log_fase3_ulang_tier.txt) dan M0–M6 IDHS |
| 2026-10-11 13:08 | Tag v-paper1 (tier 3) |
| 2026-10-25 06:02 | Run 4 benchmark v1 selesai (kode tag, tier 3) |

Komentar AUDIT di snapshot pra-audit: AUDIT: hambatan_biaya diperlakukan sebagai confounder, padahal PBI (JKN gratis) masuk akal MENURUNKAN hambatan biaya -> hambatan_biaya bisa mediator. Bila disetujui, ganti "skor_kekayaan_nonwash -> hambatan_biaya" + "hambatan_biaya -> {Y}" dengan menambah "{T} -> hambatan_biaya", dan pindahkan hambatan_biaya ke tier 3 (lihat TIER). / AUDIT: kekayaan, hambatan_biaya/jarak, dan PBI diukur saat wawancara 2017, sedangkan persalinan dan kematian neonatal bisa terjadi hingga 5 tahun sebelumnya. Tier di bawah tidak mencerminkan urutan waktu sebenarnya untuk outcome kelahiran -> tulis sebagai keterbatasan. / AUDIT: hambatan_biaya (tier 2) dan hambatan_jarak (tier 3) berasal dari jenis pertanyaan yang sama; samakan tier-nya (usul: keduanya 3).

Apakah keputusan diambil sesudah melihat hasil run 3: rencana dan alasan perubahan sudah tertulis sebelum run 3 dimulai (runbook dan komentar AUDIT pada snapshot pra-audit), dan isi commit 98841d0 sama dengan blok di runbook. Pelaksanaannya terjadi sekitar 9 jam sesudah run 3 selesai. Pernyataan penulis: hasil run 3 sudah dilihat sebelum perubahan tier dilaksanakan; perubahan itu mengikuti langkah 3.1 runbook yang tertulis sebelum run 3 dimulai. Repositori hanya dapat membuktikan bahwa rencana tertulis lebih dulu, tidak dapat membuktikan bahwa keputusan pelaksanaan tidak dipengaruhi hasil run 3. Karena itu perubahan ini diperlakukan sebagai deviasi.

Letak deviasi: runbook hanya meminta baseline pbi_diare dijalankan ulang sesudah perubahan tier; benchmark v1 tidak dijalankan ulang sebelum tag dibuat, padahal runbook langkah 4 menetapkan bahwa setiap angka naskah harus dapat ditelusuri ke satu commit.

## Analisis yang dijalankan dengan tier 3

| Analisis IDHS | DAG memuat hambatan_biaya | Dijalankan di log_fase3 (sebelum 98841d0) | Dijalankan ulang di 4806252 |
|---|---|---|---|
| sanitasi_diare | tidak | kausal, sol_v2 | – |
| pbi_diare | ya | baseline, kausal, sol_v2 | N1, N2 |
| pbi_neonatal | tidak | – | – |
| fasilitas_neonatal | ya | – | N1, N2, baseline |
| sanitasi_diare_ctps | tidak | baseline, kausal, sol_v2 | – |
| pbi_diare_biaya | ya | baseline, kausal, sol_v2 | – |
| sanitasi_diare tanpa trimming | tidak | kausal | – |

- M0–M6 pada IDHS (sanitasi_diare, pbi_diare): commit 4806252, tier 3. Seluruh menu aplikasi dijalankan ulang 11-10 16:10–17:36 dan 25-10 dengan tier 3 (penyelarasan; lihat drift E3).

- Benchmark v4 (simulasi utama, selesai 11-10 10:24) tidak membaca C.TIER: DGP-nya membangkitkan tier sintetis sendiri, jadi tidak terpengaruh perubahan ini.

- Benchmark v1: run 3 (tier 2, dilaporkan) dan run 4 (tier 3).

Bukti bahwa run log_fase3 (sebelum commit 11:24) sudah memakai tier 3, dari baseline pbi_diare yang membaca tier:

| Sumber | B2 jumlah uji | B2 SHD vs pakar | B3 langkah/sisi | B3 SHD vs pakar |
|---|---|---|---|---|
| log_baseline_pbi_diare.txt (Fase 1, 10-10, tier 2) | 4803 | 31 | 41 | 35 |
| log_fase3.txt (11-10, sebelum 11:24) | 4811 | 30 | 42 | 36 |
| naskah/data (salinan beku naskah) | – | 30 | 42 | 36 |

## N3-3. Pemisahan efek konfigurasi basi dari efek perbaikan kode

Run gabungan: kode sekarang (sesudah audit A1–A6), tier hambatan_biaya = 2, dan seluruh 12 nilai config_old yang berbeda dari config.py; 7 di antaranya dibaca benchmark v1. Nilai yang tidak dibaca tidak memengaruhi hasil, tetapi ikut dipasang agar run ini setara dengan "konfigurasi basi + kode sekarang".

| blok | kunci | config_sekarang | config_old | dibaca_benchmark |
|---|---|---|---|---|
| BASELINE | alpha | 0.05 | 0.01 | ya |
| BASELINE | boot | 500 | 100 | tidak |
| BASELINE | skor | gauss | bic | ya |
| NOVELTY | boot | 500 | 100 | tidak |
| NOVELTY | sd_alpha | 0.05 | 0.01 | ya |
| NOVELTY | sd_skor | gauss | bic | ya |
| NOVELTY | sim_rep | 1000 | 200 | tidak |
| NOVELTY | to_skor | gauss | bic | ya |
| SOL | alpha | 0.05 | 0.01 | ya |
| SOL | boot | 500 | 100 | tidak |
| SOL_V2 | K | 5 | 2 | tidak |
| BENCH | n_populasi | 20 | 5 | ya |

Proporsi replikasi dengan efek dinihilkan per metode (100 replikasi per sel). Efek kode = gabungan − run 1b; efek konfigurasi = run 3 − gabungan.

| skenario | metode | Run 1b | Gabungan | Run 3 | Efek kode (pp) | Efek konfigurasi (pp) | Total (pp) | Gabungan paling dekat ke |
|---|---|---|---|---|---|---|---|---|
| A | B1 DAG pakar | 0% | 0% | 0% | 0 | 0 | 0 | sama |
| A | B2 PC + tier + IDA | 0% | 0% | 0% | 0 | 0 | 0 | sama |
| A | B3 BN skor | 23% | 23% | 35% | 0 | 12 | 12 | run 1b |
| A | N1 SD-Hybrid | 98% | 79% | 77% | -19 | -2 | -21 | run 3 |
| A | N2 TO-DAG | 98% | 79% | 77% | -19 | -2 | -21 | run 3 |
| A | SOL-DAG | 97% | 91% | 93% | -6 | 2 | -4 | run 3 |
| A | SOL tanpa koreksi desain | 65% | 64% | 59% | -1 | -5 | -6 | run 1b |
| A | SOL tanpa tier | 97% | 92% | 93% | -5 | 1 | -4 | run 3 |
| A | SOL tanpa pemisahan sampel | 98% | 77% | 77% | -21 | 0 | -21 | run 3 |
| B | SOL-DAG | 26% | 15% | 10% | -11 | -5 | -16 | run 3 |
| B | SOL tanpa MLC | 68% | 63% | 24% | -5 | -39 | -44 | run 1b |
| B | N3 MLC-DAG | 1% | 0% | 0% | -1 | 0 | -1 | run 3 |
| B | N3 tanpa konstruk | 2% | 7% | 3% | 5 | -4 | 1 | run 3 |
| B | B2 indikator mentah | 0% | 0% | 0% | 0 | 0 | 0 | sama |
| B | B3 indikator mentah | 6% | 3% | 0% | -3 | -3 | -6 | sama |

- Validasi titik antara: metode baseline skenario A (B1–B3), yang tidak tersentuh perbaikan kode, identik dengan run 1b pada 30 dari 30 nilai ringkasan (toleransi 10⁻¹²). Jadi run 1b memang memakai config_old, dan run gabungan sah sebagai titik antara.

- Skenario A, metode novelty (N1, N2, SOL tanpa pemisahan sampel): pergeseran 21 pp hampir seluruhnya efek kode (19–21 pp); konfigurasi menyumbang 0–2 pp. Hasil gabungan dekat ke run 3, sehingga klaim lama §6.4 (seluruh pergeseran akibat konfigurasi basi) harus diubah.

- Skenario A, B3: pergeseran 12 pp seluruhnya efek konfigurasi.

- Skenario B, SOL tanpa MLC: pergeseran 44 pp terdiri atas 39 pp efek konfigurasi dan 5 pp efek kode.

- Efek konfigurasi adalah efek gabungan tujuh parameter yang berubah bersamaan; rancangan ini tidak mengatribusikannya ke satu parameter.

Putusan H1–H5 (100 replikasi per skenario; uji Wilcoxon dengan koreksi Holm, H5 dari 2.000 pernyataan uji):

| Hipotesis | Run 1b | Gabungan | Run 3 |
|---|---|---|---|
| H1 | didukung sebagian (6/27) | didukung sebagian (9/27) | didukung sebagian (4/27) |
| H2 | didukung sebagian (3/8) | didukung sebagian (3/8) | didukung sebagian (3/8) |
| H3 | didukung sebagian (6/8) | didukung sebagian (6/8) | didukung sebagian (7/8) |
| H4 | didukung sebagian (4/8) | didukung sebagian (5/8) | didukung sebagian (6/8) |
| H5 | tidak didukung (0/2) | tidak didukung (0/2) | didukung sebagian (1/2) |

Putusan run gabungan sama dengan run 1b pada kelima hipotesis, sehingga perubahan H5 berasal dari konfigurasi. Galat tipe I uji terkoreksi (target 5%, IK Wilson 95%): 3,6% [2,9–4,6] dengan konfigurasi basi dan 4,5% [3,6–5,4] dengan konfigurasi benar; uji naif 13,8% [12,3–15,3] dan 12,8% [11,4–14,3]. H2 dan H3 bergantung pada waktu komputasi dan tidak dapat dibandingkan antar-run.

Kesamaan seluruh nilai ringkasan (15 metode × 10 metrik = 150 nilai): terhadap run1b: 39/150 identik, selisih maksimum 20,35; terhadap run3: 22/150 identik, selisih maksimum 41,68.

## N3-4. Uji penentu §6.5: skenario B penuh dengan tier 2

Kode sekarang, config.py sekarang, kecuali tier hambatan_biaya = 2; skenario B, 100 replikasi. RD benar skenario B: -0.045497793959032626 (run 3: -0.045497793959032626; identik).

| Acuan | Tingkat | Identik (≤10⁻¹²) | Selisih maksimum |
|---|---|---|---|
| Run 3 (tier 2) | ringkasan (6 metode × 10 metrik) | 60/60 | 2.1e-17 |
| Run 4 (tier 3) | ringkasan (6 metode × 10 metrik) | 33/60 | 9,50 |

> Catatan: Luaran per replikasi run 3 tidak tersimpan: per_rep.csv di hasil/benchmark ditimpa run 4, dan salinan riwayat run 3 hanya memuat ringkasan. Karena itu perbandingan per replikasi dilakukan terhadap run 4; perbandingan terhadap run 3 dilakukan pada tingkat ringkasan.

Perbandingan per replikasi tier 2 vs run 4 (kolom RD, batas IK, SHD, SID, langkah, sisi; 600 pasangan metode-replikasi). Identik bit demi bit: 456 dari 600. |ΔSID| dihitung pada replikasi yang SID-nya terdefinisi di kedua run.

| Metode | Replikasi identik | |ΔSHD| maks | |ΔSHD| rata-rata | |ΔSID| maks | |ΔSID| rata-rata | SID terdefinisi (tier 2 / run 4) | Status SID berubah | |ΔRD| maks |
|---|---|---|---|---|---|---|---|---|
| SOL-DAG | 100/100 | 0 | 0,00 | 0 | 0,00 | 100 / 100 | 0 | 0.0e+00 |
| SOL tanpa MLC | 96/100 | 0 | 0,00 | – | – | 0 / 0 | 0 | 3.7e-04 |
| N3 MLC-DAG | 100/100 | 0 | 0,00 | 0 | 0,00 | 100 / 100 | 0 | 0.0e+00 |
| N3 tanpa konstruk | 27/100 | 7 | 0,70 | 3 | 0,67 | 7 / 7 | 2 | 1.1e-03 |
| B2 indikator mentah | 82/100 | 0 | 0,00 | 1 | 0,03 | 99 / 98 | 1 | 2.8e-04 |
| B3 indikator mentah | 51/100 | 1 | 0,08 | 0 | 0,00 | 2 / 1 | 1 | 2.8e-04 |

Menjelaskan SID 9,5 vs "hingga 1 per replikasi": untuk B3 indikator mentah, SID hanya terdefinisi pada 2 dari 100 replikasi di run tier 2 (rata-rata 85,5) dan 1 dari 100 di run 4 (95,0). Selisih rata-rata 9,5 muncul karena satu replikasi berpindah dari terdefinisi menjadi tidak terdefinisi, bukan karena SID per replikasi berubah 9,5; pada replikasi yang terdefinisi di kedua run selisihnya 0. Rata-rata SID metode ini berbasis 1–2 replikasi dan sebaiknya dilaporkan bersama jumlah replikasi yang terdefinisi.

Kesimpulan N3-4: dengan tier 2, kode sekarang menghasilkan ulang run 3 pada seluruh nilai ringkasan; perubahan tier menjelaskan seluruh selisih run 3 vs run 4, termasuk SID 9,5.

## Dampak pada naskah 3

- §6.4: pergeseran 21 pp skenario A dipisah menjadi efek kode (19 pp) dan konfigurasi (2 pp); efek konfigurasi disebut efek gabungan; perubahan H5 diatribusikan ke konfigurasi dengan catatan batas tipis.

- §6.5: hasil N3-4, deviasi tier (N3-2), run 4 sebagai run kanonis (N3-1); SID B3 indikator mentah dilaporkan bersama jumlah replikasi yang terdefinisi.

- Catatan deviasi: CATATAN_DEVIASI.md bagian 5.1 dan 5.2.
