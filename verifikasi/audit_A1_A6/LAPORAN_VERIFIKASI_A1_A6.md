# Laporan Verifikasi Perbaikan Audit A1–A6

Dibuat otomatis oleh buat_laporan.py dari luaran verifikasi_a1_a6.py (dijalankan 2026-11-01 09:32, 3,7 menit; HEAD f1d96be; Python 3.13.15, numpy 2.5.3, pandas 3.0.6). SHA-256 novelty.py 88c597821d490a1f…, benchmark.py 0f8a1b6616308b8a…, config.py 641b28da6925637e….

## 1. Ringkasan

Audit A1–A6 dipasang pada commit 74eb7a4 (10-10-2026 17.00 WIB) dan dinyatakan lulus pada commit a02d204 (19.14 WIB, “Fase 1 lulus: audit terverifikasi”). Saat itu tidak dibuat dokumen yang menyatakan apa yang diperiksa dan apa kriteria lulusnya; buktinya hanya perubahan berkas log. Laporan ini menguji ulang keenam perbaikan pada kode dan data sekarang dengan uji yang dapat diulang.

| Kode | Perbaikan | Status |
|---|---|---|
| A1 | Semua modul memakai config.py, bukan config_old.py | LULUS |
| A2 | Simulasi S={z}: z menjadi confounder x dan y | LULUS |
| A3 | Aliran acak per analisis | LULUS |
| A4 | MLC-DAG memakai n efektif, bukan n mentah | LULUS |
| A5 | delta_bar tanpa variabel konteks tier 0 | LULUS |
| A6 | Treatment analisis lain tidak masuk node MLC | LULUS |

Keenam perbaikan terpasang dan bekerja sesuai rancangannya. Dua catatan substantif: (i) bukti kelulusan A2 pada 10 Oktober tidak sahih, walaupun perbaikannya sendiri benar (bagian 3); (ii) A5 tidak selalu memperbesar n efektif seperti alasan yang ditulis di kode; pada analisis PBI justru memperkecilnya (bagian 6).

## 2. A1 — konfigurasi yang benar-benar terpakai

Hasil: 18 modul aktif dipindai, 0 masih mengimpor config_old; 8 modul terimpor memakai objek config yang sama; 13 nilai config.py berbeda dari config_old.py (dulu tidak terpakai).

Sebelum audit, modul analisis mengimpor config_old.py, sehingga perubahan apa pun di config.py tidak berpengaruh tanpa tanda apa pun. Tabel berikut adalah nilai yang berbeda antara kedua berkas pada saat ini; nilai di kolom config_old adalah nilai yang dulu diam-diam dipakai.

| Objek | Kunci | config_old (dulu terpakai) | config (sekarang) |
|---|---|---|---|
| NOVELTY | boot | 100 | 500 |
| NOVELTY | sd_alpha | 0.01 | 0.05 |
| NOVELTY | sd_skor | 'bic' | 'gauss' |
| NOVELTY | sim_rep | 200 | 1000 |
| NOVELTY | to_skor | 'bic' | 'gauss' |
| BENCH | n_populasi | 5 | 20 |
| SOL | alpha | 0.01 | 0.05 |
| SOL | boot | 100 | 500 |
| SOL_V2 | K | 2 | 5 |
| TIER | hambatan_biaya | 2 | 3 |
| BASELINE | alpha | 0.01 | 0.05 |
| BASELINE | boot | 100 | 500 |
| BASELINE | skor | 'bic' | 'gauss' |

> Catatan: TIER['hambatan_biaya'] di config.py baru diubah 2 → 3 pada 11-10-2026 11.24 (commit 98841d0), sesudah audit dan sesudah run 3 selesai. Pada saat run 3, config_old dan config.py sama-sama memakai tier 2, sehingga perbedaan konfigurasi basi vs benar saat itu adalah 12 parameter, bukan 13. Dari 12 itu, benchmark v1 hanya membaca 7: α (BASELINE, NOVELTY.sd_alpha, SOL), fungsi skor (BASELINE, NOVELTY.sd_skor, NOVELTY.to_skor), dan BENCH.n_populasi; boot NOVELTY/SOL/BASELINE, sim_rep, dan SOL_V2.K tidak dibaca benchmark v1 (benchmark memakai BENCH.boot = 20).

## 3. A2 — simulasi uji bersyarat S={z}

Hasil: pasangan z tanpa pengondisian ditolak 100.0% (kontinu) dan 100.0% (biner) -> z benar confounder; dengan S={z} kembali ke 5.9% dan 5.5%. Namun keputusan S={z} kontinu sama dengan S=∅ pada 99.9% replikasi (versi pra-audit 99.9%): perbandingan baris log S={z} vs S=∅ tidak dapat membedakan versi lama dan baru.

Simulasi memakai desain sampel analisis sanitasi_diare (bobot, strata, PSU nyata), ICC 0,40, muatan z 0,6, efek 0, 2000 replikasi, α = 0,05. Baris “diagnostik” tidak pernah dilaporkan di log aplikasi; baris itulah yang menunjukkan bahwa z sungguh mengacaukan pasangan uji. Uji naif menolak terlalu sering (11–21%) pada semua kasus karena mengabaikan desain klaster; itu temuan N1, bukan bagian A2.

| Kasus | Harapan (uji terkoreksi) | Tolak, uji naif (B2) | Tolak, uji terkoreksi desain | IK 95% Wilson (terkoreksi) | p binomial vs 0,05 |
|---|---|---|---|---|---|
| kontinu: pasangan z, S=∅ (diagnostik) | harus jauh di atas α | 100,0% | 100,0% | 99,8%–100,0% | < 0,001 |
| kontinu: pasangan z, S={z} (versi audit) | ≈ α | 20,1% | 5,9% | 5,0%–7,1% | 0,057 |
| kontinu: pasangan lama, S={z} (versi pra-audit) | ≈ α | 20,1% | 5,9% | 5,0%–7,1% | 0,057 |
| kontinu: S=∅ | ≈ α | 20,0% | 5,9% | 4,9%–7,0% | 0,090 |
| biner: pasangan z, S=∅ (diagnostik) | harus jauh di atas α | 100,0% | 100,0% | 99,8%–100,0% | < 0,001 |
| biner: pasangan z, S={z} (versi audit) | ≈ α | 10,4% | 5,5% | 4,5%–6,5% | 0,356 |
| biner: pasangan lama, S={z} (versi pra-audit) | ≈ α | 10,9% | 5,7% | 4,7%–6,7% | 0,182 |
| biner: S=∅ | ≈ α | 11,7% | 5,1% | 4,2%–6,1% | 0,918 |

Pada data kontinu, uji terkoreksi menolak 5,9% (IK 95% 5,0%–7,1%): tidak berbeda bermakna dari 5% pada 2.000 replikasi, tetapi batas atasnya sekitar 7%, sehingga kemungkinan sedikit liberal belum dapat disingkirkan. Pada data biner, 5,5% (IK 95% 4,5%–6,5%). Rumusan yang aman: koreksi desain menurunkan galat tipe I dari sekitar 20% menjadi sekitar 6% pada data kontinu dan dari sekitar 11% menjadi sekitar 5% pada data biner. Kata “terkalibrasi” tidak dipakai untuk data kontinu.

Kesetaraan struktural pasangan kontinu. Baris kontinu versi audit dan pra-audit identik di kedua kolom. Ini bukan bug: residu (cz·z + sz·x) atas z sama dengan sz × residu x atas z, dan pengali skala tidak mengubah korelasi parsial maupun statistik uji. Nilai p per replikasi (A2_p_per_replikasi.csv) membuktikannya: selisih maksimum nilai p terkoreksi antara kedua pasangan 6.7e-16 (galat pembulatan), dan keputusan sama pada 100,0% replikasi. Pada data biner, dikotomisasi memutus kesetaraan ini (keputusan sama pada 90,4% replikasi). Konsekuensinya, perbaikan A2 tidak mengubah angka galat tipe I kontinu sama sekali; ia hanya membuat skenario S={z} bermakna (z kini confounder sungguhan).

Mengapa bukti 10 Oktober tidak sahih. Commit 872d0e9 (17.12) mencatat “gerbang belum lulus: baris kontinu S={z}”: baris S={z} kontinu sama persis dengan S=∅ (0,225/0,055/0,055). Pada commit a02d204 (19.14) kedua baris berbeda tipis (0,226/0,053/0,053 vs 0,225/0,053/0,053) dan audit dinyatakan lulus. Uji ulang menunjukkan bahwa keputusan uji S={z} kontinu sama dengan S=∅ pada 99,9% replikasi pada versi audit dan 99,9% pada versi pra-audit. Ini memang diharapkan: pada model linear, mengondisikan pada z menghapus komponen z sehingga sisa yang diuji praktis sama dengan pasangan tanpa z. Perbandingan baris S={z} dengan S=∅ karena itu tidak dapat membedakan kode lama dari kode baru.

Perbedaan antara kedua log juga dijelaskan oleh jumlah replikasi, bukan oleh kode: semua angka simulasi pada log 17.12 adalah kelipatan 0,005 (konsisten dengan 200 replikasi), sedangkan 27 dari 45 angka pada log 19.14 bukan kelipatan 0,005 (memerlukan ≥ 1.000 replikasi, sesuai config.py). Log 17.12 sudah memakai config.py baru (boot = 500, delta_bar = 2,26 sesudah A5), sehingga 200 replikasi kemungkinan besar berasal dari isian “Replikasi simulasi” di aplikasi (app.py baris 531), yang mengesampingkan nilai config. Tidak ada kode yang berubah di antara kedua commit (a02d204 hanya memuat berkas log).

Kesimpulan A2: perbaikannya benar dan bekerja (z kini confounder; uji bersyarat mendekati nominal), tetapi kriteria kelulusan yang dipakai pada 10 Oktober tidak menguji hal itu. Kriteria yang tepat adalah baris diagnostik di atas.

## 4. A3 — aliran acak per analisis

Hasil: berkas hasil N2 identik antara 'jalankan semua' dan 'jalankan satu' pada 5/5 analisis (kolom waktu/memori diabaikan); tiruan perilaku pra-audit (satu rng bersama) memberi RD/CI bootstrap berbeda pada 1/5 analisis. Terpisah dari rng: label 'terbaik' di banding.csv berpindah pada 1/5 analisis karena peringkat memakai waktu komputasi.

Uji memakai novelty.run() yang sesungguhnya untuk N2 TO-DAG (bootstrap 30 kali, memakai rng), dengan folder luaran dialihkan ke direktori sementara. Setiap analisis ke-2 dan seterusnya dijalankan sendiri dan dibandingkan dengan hasilnya saat semua analisis dijalankan berurutan. Kolom waktu dan memori diabaikan karena memang berubah di tiap run. Perilaku pra-audit ditiru dengan satu rng yang dipakai bersama secara berurutan.

| Analisis | Berkas hasil | Identik (versi audit) | Berbeda (tiruan pra-audit) |
|---|---|---|---|
| pbi_diare | 5 | True | False |
| pbi_neonatal | 5 | True | False |
| fasilitas_neonatal | 5 | True | False |
| sanitasi_diare_ctps | 5 | True | False |
| pbi_diare_biaya | 5 | True | True |

> Catatan: Analisis yang graf-nya tidak memuat jalur T→Y (RD = 0) tidak memakai rng, sehingga pada tiruan pra-audit pun hasilnya tidak berubah; bug pra-audit hanya tampak pada analisis sesudah analisis yang memakai bootstrap.

Temuan sampingan: label “terbaik” di banding.csv (dan di log aplikasi, “terbaik=…”) ikut ditentukan oleh peringkat waktu komputasi, sehingga dapat berpindah antara dua run yang hasil statistiknya identik. Pada verifikasi ini label berpindah pada 1 dari 5 analisis (fasilitas_neonatal: N2 → B3). Klaim “metode terbaik” dari menu novelty karena itu tidak boleh dikutip tanpa menyebut bahwa ia bergantung pada kecepatan mesin; pisahkan peringkat akurasi dari peringkat waktu.

## 5. A4 — n efektif pada MLC-DAG

Hasil: tidak ada lagi pemanggilan temukan(..., len(d)) di novelty.py/benchmark.py; n_eff MLC = 27%–44% dari n mentah.

| Analisis | n mentah (dulu dipakai) | n Kish | delta_bar | n efektif (sekarang) | n efektif / n |
|---|---|---|---|---|---|
| sanitasi_diare | 15604 | 10167.2 | 2.226 | 4568.3 | 0.293 |
| pbi_diare | 15718 | 10239.3 | 2.194 | 4666.7 | 0.297 |
| pbi_neonatal | 6385 | 4148.4 | 1.468 | 2826.4 | 0.443 |
| fasilitas_neonatal | 16158 | 10509.2 | 2.39 | 4396.5 | 0.272 |
| sanitasi_diare_ctps | 15604 | 10167.2 | 2.226 | 4568.3 | 0.293 |
| pbi_diare_biaya | 15718 | 10239.3 | 2.194 | 4666.7 | 0.297 |

Dengan n mentah, penalti skor dan uji MLC 2–4 kali terlalu lunak dibanding N1/N2, yang konsisten dengan graf MLC yang terlalu padat (68–77 sisi) yang dicatat di komentar audit. Pemeriksaan statis juga memastikan benchmark.py memakai rumus n efektif yang sama.

## 6. A5 — delta_bar tanpa variabel konteks

Hasil: delta_bar berubah dari rentang 1.28–2.77 menjadi 1.40–2.26; implementasi cocok dengan hitungan manual (rerata deff variabel tier > 0) pada 6/6 analisis. Arah perubahan: turun pada 3, naik pada 3 analisis.

| Analisis | Variabel tier 0 | deff maks tier 0 | delta_bar pra-audit | delta_bar audit | n_eff pra-audit | n_eff audit | Arah delta_bar |
|---|---|---|---|---|---|---|---|
| sanitasi_diare | cuci_tangan_klaster_lo p0_daerah_mar2017 perdesaan sanitasi_klaster_lo | 7.5 | 2.765 | 2.264 | 3823.0 | 4670.0 | turun |
| pbi_diare | p0_daerah_mar2017 pbi_pct_prov perdesaan | 1.58 | 1.937 | 2.125 | 5549.0 | 5059.0 | naik |
| pbi_neonatal | p0_daerah_mar2017 pbi_pct_prov perdesaan | 1.1 | 1.277 | 1.395 | 3516.0 | 3220.0 | naik |
| fasilitas_neonatal | fasilitas_klaster_lo jarak_klaster_lo p0_daerah_mar2017 pct_pkm_kurang_bidan perdesaan rasio_pkm_per_kec | 9.39 | 2.679 | 2.195 | 4257.0 | 5197.0 | turun |
| sanitasi_diare_ctps | cuci_tangan_klaster_lo p0_daerah_mar2017 perdesaan sanitasi_klaster_lo | 7.5 | 2.765 | 2.264 | 3823.0 | 4670.0 | turun |
| pbi_diare_biaya | p0_daerah_mar2017 pbi_pct_prov perdesaan | 1.58 | 1.937 | 2.125 | 5549.0 | 5059.0 | naik |

Alasan A5 di kode adalah bahwa variabel konteks tingkat klaster bernilai konstan di dalam PSU sehingga deff-nya besar dan menggelembungkan delta_bar. Ini benar untuk analisis sanitasi dan fasilitas (deff variabel konteks hingga 7,5–9,4). Pada analisis PBI, variabel tier 0-nya agregat provinsi/daerah dengan deff kecil (≤ 1,6); mengeluarkannya justru menaikkan delta_bar dan menurunkan n efektif 8–9%. Implementasinya sesuai rancangan, tetapi narasi “A5 memperbesar n efektif” tidak berlaku umum dan sebaiknya ditulis per analisis.

## 7. A6 — node MLC

Hasil: treatment analisis lain di node MLC: pra-audit 12 (total atas 6 analisis), sesudah audit 3, seluruhnya treatment yang memang node DAG pakar analisis tersebut (pengecualian yang disengaja).

| Analisis | Treatment analisis | Treatment di node MLC (pra-audit) | Treatment di node MLC (audit) | Treatment lain yang tersisa |
|---|---|---|---|---|
| sanitasi_diare | T_sanitasi | T_sanitasi T_pbi T_fasilitas | T_sanitasi | – |
| pbi_diare | T_pbi | T_sanitasi T_pbi T_fasilitas | T_sanitasi T_pbi | T_sanitasi |
| pbi_neonatal | T_pbi | T_sanitasi T_pbi T_fasilitas | T_pbi T_fasilitas | T_fasilitas |
| fasilitas_neonatal | T_fasilitas | T_sanitasi T_pbi T_fasilitas | T_fasilitas | – |
| sanitasi_diare_ctps | T_sanitasi | T_sanitasi T_pbi T_fasilitas | T_sanitasi | – |
| pbi_diare_biaya | T_pbi | T_sanitasi T_pbi T_fasilitas | T_sanitasi T_pbi | T_sanitasi |

Treatment lain yang tersisa (T_sanitasi pada analisis PBI-diare, T_fasilitas pada PBI-neonatal) adalah node DAG pakar analisis tersebut, sehingga dipertahankan dengan sengaja. Kasus yang memicu A6, yaitu T_pbi terpilih sebagai induk T_sanitasi pada analisis sanitasi, tidak dapat terjadi lagi karena T_pbi tidak lagi menjadi node.

## 8. Rekomendasi

- Ganti kriteria kelulusan A2 dengan baris diagnostik (pasangan z tanpa pengondisian harus jauh di atas α) dan tampilkan baris itu di log aplikasi.

- Catat jumlah replikasi simulasi di setiap baris log; isian aplikasi dapat mengesampingkan config.py tanpa jejak.

- Untuk A5, laporkan arah perubahan n efektif per analisis, bukan sebagai perbaikan seragam.

- Simpan laporan ini bersama skripnya; jalankan ulang verifikasi_a1_a6.py setiap kali novelty.py, benchmark.py, atau config.py berubah, dan bandingkan SHA-256 di bagian awal laporan.

- Kasus A1 (konfigurasi diubah tetapi tidak terpakai, tanpa galat) layak dimasukkan ke naskah 3 sebagai contoh kesalahan senyap.

## 9. Berkas

- verifikasi_a1_a6.py — skrip uji ulang (hanya membaca kode dan data; tidak menulis ke hasil/)

- A1_beda_config.csv, A2_simulasi_confounder.csv, A3_aliran_acak.csv, A4_n_eff_mlc.csv, A5_delta_bar.csv, A6_node_mlc.csv, A2_p_per_replikasi.csv — tabel hasil

- ringkasan_verifikasi.json — status, SHA-256, versi pustaka

- log_verifikasi.txt — keluaran konsol

- buat_laporan.py — penyusun laporan ini
