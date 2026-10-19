# Narasi hasil analisis IDHS 2017

## 1. Persiapan Data

### Rangkuman proses
1. Membaca recode kelahiran (IDBR71) dan rumah tangga (IDHR71) IDHS 2017 langsung dari berkas zip DHS.
2. Membatasi unit analisis pada kelahiran dalam 5 tahun sebelum survei (v008 − b3 < 60 bulan).
3. Membentuk treatment: sanitasi layak (jenis jamban v116), kepesertaan JKN PBI (v481c), dan persalinan di fasilitas kesehatan (tempat persalinan m15).
4. Membentuk outcome: diare 2 minggu terakhir (h11, hanya anak hidup), ISPA, kematian neonatal (meninggal < 1 bulan, b5–b6), dan kematian bayi (b7).
5. Menyusun kovariat ibu, anak, dan rumah tangga, termasuk indeks kekayaan non-WASH dari PCA aset tanpa komponen air, jamban, dan ternak.
6. Menghitung agregat klaster leave-one-out (cakupan sanitasi, cuci tangan, fasilitas, hambatan jarak).
7. Menggabungkan data konteks provinsi 2017 (kemiskinan, puskesmas per kecamatan, kekurangan bidan, cakupan PBI).
8. Menyimpan dataset ke cache/analisis.pkl dan hasil/dataset_analisis.csv beserta bobot (v005/10⁶), PSU (v021), dan strata (v023).

### Narasi
Dataset analisis memuat **17.848 kelahiran** dalam lima tahun terakhir dari 1.967 klaster di 34 provinsi, dengan 63 variabel. Setiap kelahiran membawa bobot sampel, PSU, dan strata sehingga seluruh estimasi pada menu berikutnya mewakili populasi Indonesia dan memperhitungkan desain survei berklaster.

Secara berbobot, 74,3% kelahiran tinggal di rumah tangga dengan sanitasi layak, 29,7% ibu tercatat sebagai peserta JKN PBI, dan 79,4% persalinan terjadi di fasilitas kesehatan. Prevalensi diare balita dalam dua minggu terakhir sebesar 14,2%, sedangkan kematian neonatal sebesar 1,54% (295 kasus dalam sampel).

Data kosong pada treatment dan outcome sebagian besar bersifat struktural, misalnya diare hanya ditanyakan untuk anak yang masih hidup dan kematian bayi hanya dinilai bagi anak yang sudah terpapar 12 bulan: Y_mati_bayi 19,4%, Y_diare 3,9%, Y_ispa 3,8%, T_sanitasi 3,6%. Analisis kausal memakai kasus lengkap per analisis.

Indeks kekayaan non-WASH (komponen utama pertama) menjelaskan 22,0% varians aset. Komponen air, jamban, dan ternak sengaja dikeluarkan agar indeks kekayaan tidak tumpang tindih dengan treatment sanitasi dan faktor risiko diare.

## 2. Eksplorasi Data

### Rangkuman proses
1. Menghitung rerata berbobot dan SE linearisasi Taylor (strata, PSU) untuk 15 variabel utama, beserta CI 95%.
2. Menghitung design effect (deff) treatment dan outcome sebagai rasio varians desain terhadap varians sampel acak sederhana.
3. Meringkas treatment dan outcome per kuintil kekayaan non-WASH dan per provinsi.
4. Menghitung standardized mean difference (SMD) berbobot seluruh kovariat antara kelompok treatment dan kontrol.
5. Menghitung proporsi data kosong dan matriks korelasi variabel utama.

### Narasi
Prevalensi berbobot (CI 95%): kepesertaan JKN PBI 29,7% (28,5–30,9%); sanitasi layak 74,3% (72,8–75,8%); persalinan di fasilitas kesehatan 79,4% (78,0–80,8%); diare pada balita (2 minggu terakhir) 14,2% (13,4–14,9%); ISPA pada balita 4,21% (3,81–4,62%); kematian neonatal 1,54% (1,32–1,76%); kematian bayi 2,31% (2,00–2,62%).

Design effect berkisar 1,49–5,59 (diare 2,17). Artinya, karena pengambilan sampel berklaster, ukuran sampel efektif hanya sekitar n/deff; mengabaikan desain survei akan membuat standard error terlalu kecil dan uji terlalu sering menolak hipotesis nol.

Terdapat gradien sosial-ekonomi yang jelas: sanitasi layak naik dari 45,0% pada kuintil termiskin menjadi 94,9% pada kuintil terkaya; persalinan di fasilitas kesehatan naik dari 54,3% pada kuintil termiskin menjadi 94,7% pada kuintil terkaya; kepesertaan JKN PBI turun dari 45,7% pada kuintil termiskin menjadi 12,6% pada kuintil terkaya; diare pada balita (2 minggu terakhir) turun dari 15,6% pada kuintil termiskin menjadi 11,1% pada kuintil terkaya. Karena kekayaan memengaruhi treatment sekaligus outcome, kekayaan adalah confounder utama yang wajib dikontrol.

Variasi antarprovinsi besar: sanitasi layak 39,1% (Bengkulu) hingga 90,3% (DI Yogyakarta); kepesertaan JKN PBI 8,5% (Kep. Riau) hingga 68,3% (Aceh); persalinan di fasilitas kesehatan 28,7% (Maluku) hingga 100,0% (DI Yogyakarta). Variasi ini dimanfaatkan melalui variabel konteks provinsi dan agregat klaster dalam DAG.

Kelompok treatment dan kontrol tidak sebanding sebelum penyesuaian: kepesertaan JKN PBI memiliki 23 kovariat dengan |SMD| > 0,1 (terbesar jkn_nonpbi -0,97, kuintil_kekayaan_nonwash -0,59, skor_kekayaan_nonwash -0,56); sanitasi layak memiliki 28 kovariat dengan |SMD| > 0,1 (terbesar sanitasi_klaster_lo 1,21, skor_kekayaan_nonwash 1,00, kuintil_kekayaan_nonwash 0,99); persalinan di fasilitas kesehatan memiliki 26 kovariat dengan |SMD| > 0,1 (terbesar fasilitas_klaster_lo 1,71, skor_kekayaan_nonwash 0,93, kuintil_kekayaan_nonwash 0,88). Perbandingan naif akan bias oleh confounding, sehingga penyesuaian kovariat berbasis DAG pada menu 3 diperlukan.

Variabel dengan data kosong > 5%: jarak_sumur_septik_m (71,0%), Y_mati_bayi (19,4%), M_anc4 (14,4%). Variabel dengan kekosongan tinggi tidak dipakai di DAG kecuali memang diperlukan.

## 3. Inferensi Kausal — sanitasi_diare

### Rangkuman proses
1. Membangun DAG pakar (29 panah) untuk sanitasi layak → diare pada balita (2 minggu terakhir) dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: air_layak, anak_laki, cuci_tangan_dasar, cuci_tangan_klaster_lo, olah_air_efektif, org_per_kamar, p0_daerah_mar2017, pend_ibu_thn, perdesaan, punya_ternak, sanitasi_klaster_lo, skor_kekayaan_nonwash, umur_anak_bln dikontrol.
3. Membatasi data ke kasus lengkap: n = 16.232 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek sanitasi layak terhadap diare pada balita (2 minggu terakhir) **teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor.

Estimator utama AIPW pada 16.232 kelahiran menunjukkan bahwa sanitasi layak **menurunkan risiko diare pada balita (2 minggu terakhir) sebesar 3,38 poin persen** (RD -0,0338; CI 95% [-0,0569; -0,0121]), setara RR 0,79 (CI 95% 0,69–0,92). Risiko terprediksi 13,02% bila seluruh populasi menerima treatment dibanding 16,40% bila tidak. Efek ini bermakna secara statistik (CI 95% tidak memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD -0,0194 dan IPW -0,0362. Ketiga estimator searah dengan selisih terbesar 1,67 poin persen; perbedaan ini menandakan hasil peka terhadap spesifikasi model propensity atau outcome.

Pembobotan IPW menurunkan |SMD| maksimum dari 1,19 menjadi 0,11, sedikit di atas ambang 0,1; masih ada ketidakseimbangan kecil yang dikoreksi oleh komponen model outcome pada AIPW.

E-value sebesar 1,83 (batas CI 1,40): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,83 untuk menghapus estimasi titik, dan minimal 1,40 untuk menggeser CI hingga memuat 1.

## 3. Inferensi Kausal — pbi_diare

### Rangkuman proses
1. Membangun DAG pakar (25 panah) untuk kepesertaan JKN PBI → diare pada balita (2 minggu terakhir) dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: T_sanitasi, air_layak, anak_laki, hambatan_biaya, ibu_bekerja, jml_art, kk_perempuan, p0_daerah_mar2017, pbi_pct_prov, pend_ibu_thn, perdesaan, skor_kekayaan_nonwash, umur_anak_bln dikontrol.
3. Membatasi data ke kasus lengkap: n = 16.508 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek kepesertaan JKN PBI terhadap diare pada balita (2 minggu terakhir) **teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor.

Estimator utama AIPW pada 16.508 kelahiran menunjukkan bahwa kepesertaan JKN PBI **meningkatkan risiko diare pada balita (2 minggu terakhir) sebesar 2,46 poin persen** (RD 0,0246; CI 95% [0,0083; 0,0417]), setara RR 1,18 (CI 95% 1,06–1,32). Risiko terprediksi 16,00% bila seluruh populasi menerima treatment dibanding 13,54% bila tidak. Efek ini bermakna secara statistik (CI 95% tidak memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD 0,0194 dan IPW 0,0257. Ketiga estimator searah dengan selisih terbesar 0,64 poin persen; hasilnya cukup konsisten.

Pembobotan IPW menurunkan |SMD| maksimum dari 0,56 menjadi 0,03, di bawah ambang 0,1 sehingga kovariat seimbang.

E-value sebesar 1,65 (batas CI 1,31): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,65 untuk menghapus estimasi titik, dan minimal 1,31 untuk menggeser CI hingga memuat 1.

## 3. Inferensi Kausal — pbi_neonatal

### Rangkuman proses
1. Membangun DAG pakar (20 panah) untuk kepesertaan JKN PBI → kematian neonatal dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: jml_art, kembar, kk_perempuan, p0_daerah_mar2017, pbi_pct_prov, pend_ibu_thn, perdesaan, skor_kekayaan_nonwash, umur_ibu, urutan_lahir dikontrol; mediator T_fasilitas sengaja tidak dikontrol.
3. Membatasi data (umur_anak_bln < 24) ke kasus lengkap: n = 6.968 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek kepesertaan JKN PBI terhadap kematian neonatal **teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor. T_fasilitas diperlakukan sebagai mediator dan tidak dikontrol, sehingga estimasi merupakan efek total.

Estimator utama AIPW pada 6.968 kelahiran menunjukkan bahwa kepesertaan JKN PBI **menurunkan risiko kematian neonatal sebesar 0,11 poin persen** (RD -0,0011; CI 95% [-0,0071; 0,0054]), setara RR 0,92 (CI 95% 0,54–1,44). Risiko terprediksi 1,28% bila seluruh populasi menerima treatment dibanding 1,39% bila tidak. Efek ini tidak bermakna secara statistik (CI 95% memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD -0,0008 dan IPW -0,0022. Ketiga estimator searah dengan selisih terbesar 0,14 poin persen; hasilnya cukup konsisten.

Pembobotan IPW menurunkan |SMD| maksimum dari 0,54 menjadi 0,02, di bawah ambang 0,1 sehingga kovariat seimbang.

E-value sebesar 1,40 (batas CI 1,00): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,40 untuk menghapus estimasi titik; karena CI sudah memuat 1, efek belum dapat dibedakan dari nol.

## 3. Inferensi Kausal — fasilitas_neonatal

### Rangkuman proses
1. Membangun DAG pakar (30 panah) untuk persalinan di fasilitas kesehatan → kematian neonatal dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: anak_laki, fasilitas_klaster_lo, hambatan_biaya, hambatan_jarak, jarak_klaster_lo, kembar, p0_daerah_mar2017, pct_pkm_kurang_bidan, pend_ibu_thn, perdesaan, rasio_pkm_per_kec, skor_kekayaan_nonwash, umur_ibu, urutan_lahir dikontrol; laten risiko_kehamilan.
3. Membatasi data ke kasus lengkap: n = 17.607 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek persalinan di fasilitas kesehatan terhadap kematian neonatal **tidak teridentifikasi sepenuhnya** karena ada confounder laten (risiko_kehamilan) yang tidak terukur; estimasi berikut berisiko bias dan harus dibaca bersama E-value.

Estimator utama AIPW pada 17.607 kelahiran menunjukkan bahwa persalinan di fasilitas kesehatan **menurunkan risiko kematian neonatal sebesar 0,31 poin persen** (RD -0,0031; CI 95% [-0,0130; 0,0053]), setara RR 0,80 (CI 95% 0,48–1,71). Risiko terprediksi 1,24% bila seluruh populasi menerima treatment dibanding 1,55% bila tidak. Efek ini tidak bermakna secara statistik (CI 95% memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD 0,0010 dan IPW -0,0036. Ketiga estimator tidak searah dengan selisih terbesar 0,46 poin persen; perbedaan ini menandakan hasil peka terhadap spesifikasi model propensity atau outcome.

Pembobotan IPW menurunkan |SMD| maksimum dari 1,71 menjadi 0,11, sedikit di atas ambang 0,1; masih ada ketidakseimbangan kecil yang dikoreksi oleh komponen model outcome pada AIPW.

E-value sebesar 1,81 (batas CI 1,00): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,81 untuk menghapus estimasi titik; karena CI sudah memuat 1, efek belum dapat dibedakan dari nol.

## 3. Inferensi Kausal — sanitasi_diare_ctps

### Rangkuman proses
1. Membangun DAG pakar (30 panah) untuk sanitasi layak → diare pada balita (2 minggu terakhir) dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: air_layak, anak_laki, cuci_tangan_klaster_lo, olah_air_efektif, org_per_kamar, p0_daerah_mar2017, pend_ibu_thn, perdesaan, punya_ternak, sanitasi_klaster_lo, skor_kekayaan_nonwash, umur_anak_bln dikontrol; mediator cuci_tangan_dasar sengaja tidak dikontrol.
3. Membatasi data ke kasus lengkap: n = 16.384 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek sanitasi layak terhadap diare pada balita (2 minggu terakhir) **teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor. cuci_tangan_dasar diperlakukan sebagai mediator dan tidak dikontrol, sehingga estimasi merupakan efek total.

Estimator utama AIPW pada 16.384 kelahiran menunjukkan bahwa sanitasi layak **menurunkan risiko diare pada balita (2 minggu terakhir) sebesar 3,09 poin persen** (RD -0,0309; CI 95% [-0,0515; -0,0108]), setara RR 0,81 (CI 95% 0,71–0,93). Risiko terprediksi 13,24% bila seluruh populasi menerima treatment dibanding 16,33% bila tidak. Efek ini bermakna secara statistik (CI 95% tidak memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD -0,0183 dan IPW -0,0336. Ketiga estimator searah dengan selisih terbesar 1,54 poin persen; perbedaan ini menandakan hasil peka terhadap spesifikasi model propensity atau outcome.

Pembobotan IPW menurunkan |SMD| maksimum dari 1,19 menjadi 0,12, sedikit di atas ambang 0,1; masih ada ketidakseimbangan kecil yang dikoreksi oleh komponen model outcome pada AIPW.

E-value sebesar 1,77 (batas CI 1,37): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,77 untuk menghapus estimasi titik, dan minimal 1,37 untuk menggeser CI hingga memuat 1.

## 3. Inferensi Kausal — pbi_diare_biaya

### Rangkuman proses
1. Membangun DAG pakar (26 panah) untuk kepesertaan JKN PBI → diare pada balita (2 minggu terakhir) dari config.py dan memastikan graf asiklik.
2. Menentukan adjustment set dengan kriteria backdoor: T_sanitasi, air_layak, anak_laki, ibu_bekerja, jml_art, kk_perempuan, p0_daerah_mar2017, pbi_pct_prov, pend_ibu_thn, perdesaan, skor_kekayaan_nonwash, umur_anak_bln dikontrol; mediator hambatan_biaya sengaja tidak dikontrol.
3. Membatasi data ke kasus lengkap: n = 16.518 kelahiran.
4. Mengestimasi propensity score dan model outcome dengan regresi logistik berbobot survei; propensity score dipangkas pada persentil 1 dan 99.
5. Menghitung efek dengan tiga estimator: g-komputasi, IPW, dan AIPW (doubly robust, estimator utama), dalam skala risk difference (RD) dan risk ratio (RR).
6. Menghitung CI 95% dengan bootstrap PSU di dalam strata (config.BOOT = 500).
7. Memeriksa keseimbangan kovariat setelah IPW, overlap propensity score, dan sensitivitas terhadap confounder tak terukur (E-value).

### Narasi
Berdasarkan DAG pakar, efek kepesertaan JKN PBI terhadap diare pada balita (2 minggu terakhir) **teridentifikasi**: himpunan kovariat yang dikontrol memblokir semua jalur backdoor. hambatan_biaya diperlakukan sebagai mediator dan tidak dikontrol, sehingga estimasi merupakan efek total.

Estimator utama AIPW pada 16.518 kelahiran menunjukkan bahwa kepesertaan JKN PBI **meningkatkan risiko diare pada balita (2 minggu terakhir) sebesar 2,41 poin persen** (RD 0,0241; CI 95% [0,0070; 0,0407]), setara RR 1,18 (CI 95% 1,05–1,31). Risiko terprediksi 15,98% bila seluruh populasi menerima treatment dibanding 13,57% bila tidak. Efek ini bermakna secara statistik (CI 95% tidak memuat nol).

Sebagai uji sensitivitas spesifikasi model, g-komputasi memberi RD 0,0187 dan IPW 0,0251. Ketiga estimator searah dengan selisih terbesar 0,64 poin persen; hasilnya cukup konsisten.

Pembobotan IPW menurunkan |SMD| maksimum dari 0,56 menjadi 0,03, di bawah ambang 0,1 sehingga kovariat seimbang.

E-value sebesar 1,63 (batas CI 1,28): confounder tak terukur harus berasosiasi dengan treatment dan outcome dengan RR minimal 1,63 untuk menghapus estimasi titik, dan minimal 1,28 untuk menggeser CI hingga memuat 1.

## 4. Baseline — sanitasi_diare

### Rangkuman proses
1. Menyiapkan data bersama: 16.232 kasus lengkap pada 15 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **kurang** (RMSEA 0,079, CFI 0,840, SRMR 0,069; χ² = 2.915,7, df = 61). Artinya, sebagian independensi bersyarat yang disiratkan DAG pakar tidak didukung data, atau ada panah yang terlewat. Dalam skala probabilitas, efek total sanitasi layak adalah -0,0194, terdiri dari efek langsung -0,0194 dan tak langsung 0,0000 (tidak ada mediator dalam DAG pakar).

**B2 (PC + tier + IDA).** Dengan 9.108 uji independensi bersyarat, PC menemukan 42 sisi berarah dan 4 sisi tak berarah. Dibanding DAG pakar, 19 sisi sama, 27 sisi tambahan, 10 sisi hilang, dan 2 berbeda arah (SHD = 39). Induk pasti T_sanitasi: sanitasi_klaster_lo, pend_ibu_thn, org_per_kamar, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD -0,0185; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 50 langkah dengan 50 sisi; skor akhir -325.242,0 lebih tinggi daripada skor DAG pakar -333.284,2 pada skor yang sama (SHD = 41). Graf B3 memuat jalur berarah dari treatment ke outcome sehingga efek dihitung dengan inferensi do.

**Perbandingan estimasi** (RD, CI 95%): B1 -0,0194 [-0,0381; -0,0004]; B2 -0,0185 [-0,0361; 0,0006]; B3 -0,0201 [-0,0399; -0,0016]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B2 PC + tier + IDA** (peringkat rata-rata 1,67; unggul pada lebar CI), dengan RD -0,0185 yang tidak bermakna secara statistik (CI 95% memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## 4. Baseline — pbi_diare

### Rangkuman proses
1. Menyiapkan data bersama: 16.508 kasus lengkap pada 15 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **baik** (RMSEA 0,037, CFI 0,964, SRMR 0,023; χ² = 606,6, df = 52). Dalam skala probabilitas, efek total kepesertaan JKN PBI adalah 0,0162, terdiri dari efek langsung 0,0162 dan tak langsung 0,0000 (tidak ada mediator dalam DAG pakar).

**B2 (PC + tier + IDA).** Dengan 4.811 uji independensi bersyarat, PC menemukan 36 sisi berarah dan 3 sisi tak berarah. Dibanding DAG pakar, 17 sisi sama, 22 sisi tambahan, 8 sisi hilang, dan 0 berbeda arah (SHD = 30). Induk pasti T_pbi: pbi_pct_prov, ibu_bekerja, jml_art, pend_ibu_thn, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD 0,0214; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 42 langkah dengan 42 sisi; skor akhir -334.330,9 lebih tinggi daripada skor DAG pakar -342.981,6 pada skor yang sama (SHD = 36). Graf B3 memuat jalur berarah dari treatment ke outcome sehingga efek dihitung dengan inferensi do.

**Perbandingan estimasi** (RD, CI 95%): B1 0,0194 [0,0037; 0,0343]; B2 0,0214 [0,0060; 0,0378]; B3 0,0203 [0,0040; 0,0367]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B3 BN berbasis skor** (peringkat rata-rata 1,67; unggul pada BIC-SEM, CFI), dengan RD 0,0203 yang bermakna secara statistik (CI 95% tidak memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## 4. Baseline — pbi_neonatal

### Rangkuman proses
1. Menyiapkan data bersama: 6.953 kasus lengkap pada 13 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **kurang** (RMSEA 0,116, CFI 0,839, SRMR 0,070; χ² = 1.331,9, df = 30). Artinya, sebagian independensi bersyarat yang disiratkan DAG pakar tidak didukung data, atau ada panah yang terlewat. Dalam skala probabilitas, efek total kepesertaan JKN PBI adalah -0,0022, terdiri dari efek langsung -0,0023 dan tak langsung 0,0002 (melalui mediator).

**B2 (PC + tier + IDA).** Dengan 2.345 uji independensi bersyarat, PC menemukan 23 sisi berarah dan 5 sisi tak berarah. Dibanding DAG pakar, 10 sisi sama, 18 sisi tambahan, 10 sisi hilang, dan 0 berbeda arah (SHD = 28). Induk pasti T_pbi: pbi_pct_prov, jml_art, pend_ibu_thn, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD -0,0014; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 34 langkah dengan 34 sisi; skor akhir -119.443,1 lebih tinggi daripada skor DAG pakar -124.446,4 pada skor yang sama (SHD = 30). Graf B3 **tidak memuat jalur berarah dari T_pbi ke Y_mati_neonatal**, sehingga menurut graf ini efek kausalnya nol. Hal ini lazim terjadi pada outcome langka atau lemah: penalti BIC menghapus sisi yang penambahan kecocokannya kecil.

**Perbandingan estimasi** (RD, CI 95%): B1 -0,0011 [-0,0064; 0,0052]; B2 -0,0014 [-0,0070; 0,0045]; B3 0,0000 [0,0000; 0,0000]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B3 BN berbasis skor** (peringkat rata-rata 1,00; unggul pada BIC-SEM, CFI), dengan RD 0,0000 yang tidak bermakna secara statistik (CI 95% memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## 4. Baseline — fasilitas_neonatal

### Rangkuman proses
1. Menyiapkan data bersama: 17.607 kasus lengkap pada 16 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **kurang** (RMSEA 0,118, CFI 0,815, SRMR 0,079; χ² = 6.367,7, df = 56). Artinya, sebagian independensi bersyarat yang disiratkan DAG pakar tidak didukung data, atau ada panah yang terlewat. Dalam skala probabilitas, efek total persalinan di fasilitas kesehatan adalah -0,0027, terdiri dari efek langsung -0,0027 dan tak langsung 0,0000 (tidak ada mediator dalam DAG pakar).

**B2 (PC + tier + IDA).** Dengan 7.866 uji independensi bersyarat, PC menemukan 40 sisi berarah dan 2 sisi tak berarah. Dibanding DAG pakar, 13 sisi sama, 29 sisi tambahan, 15 sisi hilang, dan 2 berbeda arah (SHD = 46). Induk pasti T_fasilitas: fasilitas_klaster_lo, pend_ibu_thn, urutan_lahir, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD 0,0019; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 51 langkah dengan 51 sisi; skor akhir -365.852,9 lebih tinggi daripada skor DAG pakar -384.364,7 pada skor yang sama (SHD = 54). Graf B3 **tidak memuat jalur berarah dari T_fasilitas ke Y_mati_neonatal**, sehingga menurut graf ini efek kausalnya nol. Hal ini lazim terjadi pada outcome langka atau lemah: penalti BIC menghapus sisi yang penambahan kecocokannya kecil.

**Perbandingan estimasi** (RD, CI 95%): B1 0,0010 [-0,0057; 0,0058]; B2 0,0019 [-0,0046; 0,0069]; B3 0,0000 [0,0000; 0,0000]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B3 BN berbasis skor** (peringkat rata-rata 1,00; unggul pada BIC-SEM, CFI), dengan RD 0,0000 yang tidak bermakna secara statistik (CI 95% memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## 4. Baseline — sanitasi_diare_ctps

### Rangkuman proses
1. Menyiapkan data bersama: 16.232 kasus lengkap pada 15 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **kurang** (RMSEA 0,079, CFI 0,844, SRMR 0,068; χ² = 2.844,0, df = 60). Artinya, sebagian independensi bersyarat yang disiratkan DAG pakar tidak didukung data, atau ada panah yang terlewat. Dalam skala probabilitas, efek total sanitasi layak adalah -0,0196, terdiri dari efek langsung -0,0194 dan tak langsung -0,0002 (melalui mediator).

**B2 (PC + tier + IDA).** Dengan 9.108 uji independensi bersyarat, PC menemukan 42 sisi berarah dan 4 sisi tak berarah. Dibanding DAG pakar, 20 sisi sama, 26 sisi tambahan, 10 sisi hilang, dan 2 berbeda arah (SHD = 38). Induk pasti T_sanitasi: sanitasi_klaster_lo, pend_ibu_thn, org_per_kamar, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD -0,0185; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 50 langkah dengan 50 sisi; skor akhir -325.242,0 lebih tinggi daripada skor DAG pakar -333.219,4 pada skor yang sama (SHD = 41). Graf B3 memuat jalur berarah dari treatment ke outcome sehingga efek dihitung dengan inferensi do.

**Perbandingan estimasi** (RD, CI 95%): B1 -0,0193 [-0,0365; -0,0012]; B2 -0,0185 [-0,0375; -0,0008]; B3 -0,0201 [-0,0388; -0,0020]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B3 BN berbasis skor** (peringkat rata-rata 1,67; unggul pada BIC-SEM, CFI), dengan RD -0,0201 yang bermakna secara statistik (CI 95% tidak memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## 4. Baseline — pbi_diare_biaya

### Rangkuman proses
1. Menyiapkan data bersama: 16.508 kasus lengkap pada 15 variabel teramati DAG pakar, masing-masing diberi tier waktu (konteks → demografi → ekonomi → WASH/akses → layanan persalinan → outcome).
2. B1: mengestimasi DAG pakar sebagai SEM (analisis jalur ML dengan kovarians berbobot survei), menilai kecocokan dengan n efektif = n/2,16, mendekomposisi efek langsung dan tak langsung, lalu menghitung ulang efek dalam skala probabilitas dengan probit + g-komputasi.
3. B2: menjalankan PC-stable (uji campuran, α = 0,05, himpunan kondisi ≤ 3), mengorientasikan v-structure, pengetahuan tier, dan aturan Meek R1–R4 menjadi CPDAG, lalu menghitung himpunan efek dengan IDA.
4. B3: mencari DAG dengan Hill-Climbing ber-tier (skor GAUSS, graf awal kosong, induk maks. 5), lalu inferensi do dengan g-komputasi.
5. Langkah estimasi bersama untuk semua metode: adjustment set backdoor dari graf masing-masing → g-komputasi berbobot survei → CI 95% bootstrap PSU.
6. Rangkuman: graf setiap metode dinilai dengan SEM berbobot yang sama (BIC-SEM, CFI) dan presisi estimasi (lebar CI), lalu diperingkat untuk memilih metode terbaik.

### Narasi
**B1 (DAG pakar + SEM).** Kecocokan DAG pakar dengan data tergolong **baik** (RMSEA 0,038, CFI 0,964, SRMR 0,023; χ² = 605,1, df = 51). Dalam skala probabilitas, efek total kepesertaan JKN PBI adalah 0,0161, terdiri dari efek langsung 0,0162 dan tak langsung -0,0002 (melalui mediator).

**B2 (PC + tier + IDA).** Dengan 4.811 uji independensi bersyarat, PC menemukan 36 sisi berarah dan 3 sisi tak berarah. Dibanding DAG pakar, 17 sisi sama, 22 sisi tambahan, 9 sisi hilang, dan 0 berbeda arah (SHD = 31). Induk pasti T_pbi: pbi_pct_prov, ibu_bekerja, jml_art, pend_ibu_thn, skor_kekayaan_nonwash. IDA menghasilkan 1 himpunan induk dengan RD 0,0214; karena hanya satu, pengetahuan tier cukup untuk menetapkan efek secara unik.

**B3 (BN berbasis skor).** Hill-Climbing berhenti setelah 42 langkah dengan 42 sisi; skor akhir -334.330,9 lebih tinggi daripada skor DAG pakar -342.982,9 pada skor yang sama (SHD = 35). Graf B3 memuat jalur berarah dari treatment ke outcome sehingga efek dihitung dengan inferensi do.

**Perbandingan estimasi** (RD, CI 95%): B1 0,0191 [0,0048; 0,0368]; B2 0,0214 [0,0054; 0,0373]; B3 0,0203 [0,0056; 0,0377]. Metode yang menghasilkan efek tak nol sepakat pada arah efek.

**Metode terbaik: B2 PC + tier + IDA** (peringkat rata-rata 1,67; unggul pada lebar CI), dengan RD 0,0214 yang bermakna secara statistik (CI 95% tidak memuat nol). Karena tidak ada ground truth, *terbaik* berarti graf paling sesuai data (setelah memperhitungkan kesederhanaan) dan estimasi paling presisi, bukan jaminan paling benar secara kausal. Temuan ini menjadi pembanding bagi SOL-DAG: kelemahan bersama ketiga baseline adalah penemuan graf yang belum memperhitungkan desain survei.

## N1 SD-Hybrid — sanitasi_diare

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 16.232 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 2,26 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 4.670.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (6343 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1885) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **42 sisi** dibanding 46 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 4.670, bukan n = 16.232, sehingga graf akhir memuat 36 sisi (SHD terhadap DAG pakar 35). Graf yang ditemukan **tidak memuat jalur berarah dari T_sanitasi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 12,1% vs terkoreksi 4,5%; 3×3 (df 4), S=∅ naif 11,4% vs terkoreksi 4,3%; biner 2×2, S={z} naif 10,7% vs terkoreksi 5,1%; kontinu, S=∅ naif 22,5% vs terkoreksi 5,3%; kontinu, S={z} naif 22,6% vs terkoreksi 5,3% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 74,6% vs naif disesuaikan ukuran 90,9%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 77,5% vs naif disesuaikan ukuran 92,8%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 55,4% vs naif disesuaikan ukuran 72,5%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 92,7% vs naif disesuaikan ukuran 98,4%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 92,8% vs naif disesuaikan ukuran 98,5%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 99,2% vs naif disesuaikan ukuran 100,0%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 3,00). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N1 SD-Hybrid — pbi_diare

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 16.508 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 2,12 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 5.059.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (3147 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1900) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **33 sisi** dibanding 39 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 5.059, bukan n = 16.508, sehingga graf akhir memuat 26 sisi (SHD terhadap DAG pakar 25). Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 12,4% vs terkoreksi 4,5%; 3×3 (df 4), S=∅ naif 13,8% vs terkoreksi 6,6%; biner 2×2, S={z} naif 12,2% vs terkoreksi 6,9%; kontinu, S=∅ naif 21,5% vs terkoreksi 6,6%; kontinu, S={z} naif 21,3% vs terkoreksi 6,4% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 73,9% vs naif disesuaikan ukuran 89,7%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 78,1% vs naif disesuaikan ukuran 91,2%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 54,0% vs naif disesuaikan ukuran 70,2%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 92,3% vs naif disesuaikan ukuran 98,6%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 92,4% vs naif disesuaikan ukuran 98,6%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 99,1% vs naif disesuaikan ukuran 99,9%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 3,00). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N1 SD-Hybrid — pbi_neonatal

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 6.953 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 1,40 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 3.220.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (1248 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1828) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **24 sisi** dibanding 28 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 3.220, bukan n = 6.953, sehingga graf akhir memuat 23 sisi (SHD terhadap DAG pakar 25). Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_mati_neonatal**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 8,6% vs terkoreksi 4,5%; 3×3 (df 4), S=∅ naif 8,2% vs terkoreksi 5,5%; biner 2×2, S={z} naif 6,6% vs terkoreksi 4,3%; kontinu, S=∅ naif 12,4% vs terkoreksi 5,9%; kontinu, S={z} naif 12,4% vs terkoreksi 5,7% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 49,1% vs naif disesuaikan ukuran 61,0%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 47,3% vs naif disesuaikan ukuran 66,9%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 31,4% vs naif disesuaikan ukuran 45,3%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 77,3% vs naif disesuaikan ukuran 88,7%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 77,2% vs naif disesuaikan ukuran 88,6%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 96,7% vs naif disesuaikan ukuran 99,6%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 98,4% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 86,0% vs naif disesuaikan ukuran 96,0%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-2 dari 4 metode yang diperingkat (peringkat rata-rata 2,33). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N1 SD-Hybrid — fasilitas_neonatal

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 17.607 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 2,19 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 5.197.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (4758 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1892) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **38 sisi** dibanding 42 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 5.197, bukan n = 17.607, sehingga graf akhir memuat 33 sisi (SHD terhadap DAG pakar 40). Graf yang ditemukan **tidak memuat jalur berarah dari T_fasilitas ke Y_mati_neonatal**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 11,4% vs terkoreksi 5,0%; 3×3 (df 4), S=∅ naif 12,1% vs terkoreksi 4,9%; biner 2×2, S={z} naif 11,4% vs terkoreksi 5,6%; kontinu, S=∅ naif 20,8% vs terkoreksi 5,3%; kontinu, S={z} naif 20,8% vs terkoreksi 5,3% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 77,1% vs naif disesuaikan ukuran 89,9%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 79,2% vs naif disesuaikan ukuran 93,5%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 55,8% vs naif disesuaikan ukuran 72,9%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 92,6% vs naif disesuaikan ukuran 98,5%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 92,7% vs naif disesuaikan ukuran 98,5%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 99,5% vs naif disesuaikan ukuran 100,0%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-2 dari 4 metode yang diperingkat (peringkat rata-rata 2,33). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N1 SD-Hybrid — sanitasi_diare_ctps

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 16.232 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 2,26 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 4.670.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (6343 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1885) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **42 sisi** dibanding 46 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 4.670, bukan n = 16.232, sehingga graf akhir memuat 36 sisi (SHD terhadap DAG pakar 35). Graf yang ditemukan **tidak memuat jalur berarah dari T_sanitasi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 10,7% vs terkoreksi 5,2%; 3×3 (df 4), S=∅ naif 13,0% vs terkoreksi 5,3%; biner 2×2, S={z} naif 9,8% vs terkoreksi 4,3%; kontinu, S=∅ naif 20,0% vs terkoreksi 4,7%; kontinu, S={z} naif 19,8% vs terkoreksi 4,7% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 76,3% vs naif disesuaikan ukuran 91,5%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 78,8% vs naif disesuaikan ukuran 91,0%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 56,5% vs naif disesuaikan ukuran 71,4%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 93,5% vs naif disesuaikan ukuran 98,6%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 93,5% vs naif disesuaikan ukuran 98,7%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 99,4% vs naif disesuaikan ukuran 100,0%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 3,00). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N1 SD-Hybrid — pbi_diare_biaya

### Rangkuman proses
1. Menyiapkan data yang sama dengan baseline: 16.508 kasus lengkap, tier waktu, bobot, PSU, strata.
2. Menghitung design effect umum δ̄ = 2,12 (rerata deff klaster seluruh variabel, linearisasi Taylor) dan ukuran sampel efektif n_eff = n_Kish/δ̄ = 5.059.
3. Membangun skeleton PC-stable dengan uji terkoreksi desain (3147 uji, α = 0,05): Rao-Scott orde 1 bila semua variabel uji diskret, t-desain (korelasi parsial berbobot, varians fungsi pengaruh per PSU, df = 1900) bila tidak.
4. Mencari DAG dengan Hill-Climbing ber-tier yang dibatasi pada skeleton, memakai skor pseudo-likelihood berbobot (GAUSS) dengan penalti (k/2)·log n_eff.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
Koreksi desain membuat skeleton lebih jarang: **33 sisi** dibanding 39 sisi pada B2 yang memakai uji naif dengan α sama. Sisi yang hilang adalah hubungan yang hanya tampak bermakna karena statistik uji naif membesar akibat pengelompokan klaster. Penalti skor juga memakai n_eff = 5.059, bukan n = 16.508, sehingga graf akhir memuat 26 sisi (SHD terhadap DAG pakar 26). Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

**Simulasi galat tipe I** (H0 benar, desain IDHS nyata, ICC 0,40): biner 2×2, S=∅ naif 12,8% vs terkoreksi 4,9%; 3×3 (df 4), S=∅ naif 13,4% vs terkoreksi 4,9%; biner 2×2, S={z} naif 12,0% vs terkoreksi 5,3%; kontinu, S=∅ naif 22,7% vs terkoreksi 4,8%; kontinu, S={z} naif 23,0% vs terkoreksi 4,8% (nominal 5,0%). Ini menguji hipotesis (a) dokumen Tahap 3: uji terkoreksi seharusnya mendekati taraf nominal, sedangkan uji naif menolak terlalu sering.

**Daya uji** (efek > 0): biner 2×2, S=∅, efek 0,05: terkoreksi orde 2 74,0% vs naif disesuaikan ukuran 89,0%; 3×3 (df 4), S=∅, efek 0,05: terkoreksi orde 2 79,2% vs naif disesuaikan ukuran 92,2%; biner 2×2, S={z}, efek 0,05: terkoreksi orde 2 54,9% vs naif disesuaikan ukuran 68,2%; kontinu, S=∅, efek 0,05: terkoreksi orde 2 93,3% vs naif disesuaikan ukuran 98,2%; kontinu, S={z}, efek 0,05: terkoreksi orde 2 93,3% vs naif disesuaikan ukuran 98,2%; biner 2×2, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; 3×3 (df 4), S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; biner 2×2, S={z}, efek 0,10: terkoreksi orde 2 99,4% vs naif disesuaikan ukuran 100,0%; kontinu, S=∅, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%; kontinu, S={z}, efek 0,10: terkoreksi orde 2 100,0% vs naif disesuaikan ukuran 100,0%. Daya uji naif mentah tampak lebih tinggi hanya karena ukurannya tidak valid; setelah ambangnya dikalibrasi ke galat tipe I nominal, perbandingan daya uji menjadi adil. Koreksi desain mengorbankan sebagian daya uji untuk efek kecil, sesuai kelemahan yang diantisipasi dokumen.

**Perbandingan dengan baseline.** Dengan kriteria BIC-SEM, CFI, lebar CI, peringkat rata-rata terbaik diraih **B3 BN berbasis skor** (1,67; unggul pada BIC-SEM, CFI); N1 SD-Hybrid berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 3,00). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — sanitasi_diare

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=4 · demografi=3 · ekonomi=3 · WASH/akses=4 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 20.736 urutan, dibanding 1.308e+12 urutan tanpa tier dan 2.377e+41 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 61 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 4.670); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,20 detik** dengan memori puncak 8,3 MB dan 659 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -94.202,6 dibanding graf B3 -94.234,5 dan DAG pakar -96.333,3, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 42 sisi (SHD terhadap DAG pakar 42). Graf yang ditemukan **tidak memuat jalur berarah dari T_sanitasi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — pbi_diare

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=3 · demografi=6 · ekonomi=1 · WASH/akses=4 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 103.680 urutan, dibanding 1.308e+12 urutan tanpa tier dan 2.377e+41 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 752 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 5.059); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,21 detik** dengan memori puncak 8,4 MB dan 511 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -102.893,9 dibanding graf B3 -102.914,2 dan DAG pakar -105.528,6, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 32 sisi (SHD terhadap DAG pakar 29).

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Estimasi efeknya RD 0,0203 [0,0052; 0,0375], bermakna secara statistik (CI 95% tidak memuat nol). Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — pbi_neonatal

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=3 · demografi=6 · ekonomi=1 · WASH/akses=1 · layanan persalinan=1 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 4.320 urutan, dibanding 6.227e+09 urutan tanpa tier dan 1.868e+31 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 730 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 3.220); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,17 detik** dengan memori puncak 3,2 MB dan 532 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -55.604,3 dibanding graf B3 -55.611,7 dan DAG pakar -57.829,0, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 31 sisi (SHD terhadap DAG pakar 31). Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_mati_neonatal**, sehingga efek kausal menurut graf ini nol.

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — fasilitas_neonatal

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=6 · demografi=5 · ekonomi=1 · WASH/akses=2 · layanan persalinan=1 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 172.800 urutan, dibanding 2.092e+13 urutan tanpa tier dan 8.376e+46 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 845 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 5.197); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,30 detik** dengan memori puncak 9,6 MB dan 810 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -107.491,3 dibanding graf B3 -107.521,3 dan DAG pakar -113.769,9, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 39 sisi (SHD terhadap DAG pakar 46). Graf yang ditemukan **tidak memuat jalur berarah dari T_fasilitas ke Y_mati_neonatal**, sehingga efek kausal menurut graf ini nol.

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — sanitasi_diare_ctps

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=4 · demografi=3 · ekonomi=3 · WASH/akses=4 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 20.736 urutan, dibanding 1.308e+12 urutan tanpa tier dan 2.377e+41 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 61 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 4.670); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,24 detik** dengan memori puncak 8,3 MB dan 659 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -94.202,6 dibanding graf B3 -94.234,5 dan DAG pakar -96.315,2, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 42 sisi (SHD terhadap DAG pakar 42). Graf yang ditemukan **tidak memuat jalur berarah dari T_sanitasi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N2 TO-DAG — pbi_diare_biaya

### Rangkuman proses
1. Menyiapkan data dan tier yang sama dengan baseline (konteks=3 · demografi=6 · ekonomi=1 · WASH/akses=4 · outcome=1).
2. Membatasi ruang pencarian ke urutan yang patuh tier: |Π_τ| = 103.680 urutan, dibanding 1.308e+12 urutan tanpa tier dan 2.377e+41 DAG.
3. Karena pendahulu setiap node = seluruh tier sebelumnya + pendahulu di dalam tier-nya, F(π) terurai per tier sehingga setiap tier dioptimalkan terpisah (cukup 752 urutan diperiksa); tier ≤ 8 variabel diselesaikan eksak dengan pemrograman dinamis subset.
4. Memilih induk setiap node dengan grow-shrink (induk maks. 5) memakai skor GAUSS berbobot survei dengan penalti log n_eff (n_eff = 5.059); skor lokal disimpan dalam cache.
5. Menghitung efek dengan langkah estimasi bersama (backdoor → g-komputasi berbobot → bootstrap PSU).

### Narasi
TO-DAG menyelesaikan penemuan graf dalam **0,21 detik** dengan memori puncak 8,4 MB dan 511 skor lokal. Pada fungsi skor yang sama, skor graf TO-DAG -102.893,9 dibanding graf B3 -102.914,2 dan DAG pakar -105.532,3, artinya pencarian urutan menemukan graf yang lebih baik daripada Hill-Climbing B3. Graf akhir memuat 32 sisi (SHD terhadap DAG pakar 30).

Konvergensi terjamin: setiap tier diselesaikan eksak atau dengan pencarian pindah-posisi yang skornya naik monoton pada himpunan urutan yang hingga. Seluruh keunggulan ini bergantung pada kebenaran tier; satu variabel yang salah tier melarang panah yang benar.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, BIC-SEM, peringkat rata-rata terbaik diraih **N2 TO-DAG** (1,67; unggul pada waktu penemuan, BIC-SEM); N2 TO-DAG berada di urutan ke-1 dari 3 metode yang diperingkat (peringkat rata-rata 1,67). Estimasi efeknya RD 0,0203 [0,0044; 0,0357], bermakna secara statistik (CI 95% tidak memuat nol). Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — sanitasi_diare

### Rangkuman proses
1. Membentuk data MLC: 15.604 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 18×18.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 31 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **31 menjadi 18 node** (statistik cukup 961 → 324 entri). Tahap penemuan struktur hanya 0,420 detik (1187 skor lokal) dibanding 3,712 detik (9482 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (4,14 detik) yang dipakai bersama oleh keduanya.

Reliabilitas / jenis konstruk: eta_pendidikan=0,89, eta_kebersihan=0,32, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 45%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (2,00; unggul pada memori puncak); N3 MLC-DAG berada di urutan ke-2 dari 4 metode yang diperingkat (peringkat rata-rata 2,33). Estimasi efeknya RD -0,0190 [-0,0366; -0,0001], bermakna secara statistik (CI 95% tidak memuat nol). Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — pbi_diare

### Rangkuman proses
1. Membentuk data MLC: 15.718 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 19×19.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 32 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **32 menjadi 19 node** (statistik cukup 1.024 → 361 entri). Tahap penemuan struktur hanya 1,001 detik (2641 skor lokal) dibanding 3,150 detik (10179 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (4,24 detik) yang dipakai bersama oleh keduanya. Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

Reliabilitas / jenis konstruk: eta_pendidikan=0,89, eta_kebersihan=0,32, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 45%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (1,33; unggul pada memori puncak, lebar CI); N3 MLC-DAG berada di urutan ke-4 dari 4 metode yang diperingkat (peringkat rata-rata 3,33). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — pbi_neonatal

### Rangkuman proses
1. Membentuk data MLC: 6.385 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 17×17.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 30 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **30 menjadi 17 node** (statistik cukup 900 → 289 entri). Tahap penemuan struktur hanya 0,395 detik (1428 skor lokal) dibanding 2,517 detik (9340 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (3,46 detik) yang dipakai bersama oleh keduanya. Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_mati_neonatal**, sehingga efek kausal menurut graf ini nol.

Reliabilitas / jenis konstruk: eta_pendidikan=0,90, eta_kebersihan=0,34, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 46%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (1,33; unggul pada memori puncak, lebar CI); N3 MLC-DAG berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 2,67). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — fasilitas_neonatal

### Rangkuman proses
1. Membentuk data MLC: 16.158 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 16×16.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 29 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **29 menjadi 16 node** (statistik cukup 841 → 256 entri). Tahap penemuan struktur hanya 0,221 detik (945 skor lokal) dibanding 2,369 detik (8375 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (3,74 detik) yang dipakai bersama oleh keduanya.

Reliabilitas / jenis konstruk: eta_pendidikan=0,90, eta_kebersihan=0,33, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 45%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (1,67; unggul pada memori puncak, lebar CI); N3 MLC-DAG berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 2,67). Estimasi efeknya RD 0,0006 [-0,0066; 0,0061], tidak bermakna secara statistik (CI 95% memuat nol). Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — sanitasi_diare_ctps

### Rangkuman proses
1. Membentuk data MLC: 15.604 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 18×18.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 31 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **31 menjadi 18 node** (statistik cukup 961 → 324 entri). Tahap penemuan struktur hanya 0,226 detik (1187 skor lokal) dibanding 1,804 detik (9482 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (2,32 detik) yang dipakai bersama oleh keduanya.

Reliabilitas / jenis konstruk: eta_pendidikan=0,89, eta_kebersihan=0,32, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 45%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (2,00; unggul pada memori puncak, lebar CI); N3 MLC-DAG berada di urutan ke-3 dari 4 metode yang diperingkat (peringkat rata-rata 3,00). Estimasi efeknya RD -0,0190 [-0,0380; 0,0019], tidak bermakna secara statistik (CI 95% memuat nol). Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## N3 MLC-DAG — pbi_diare_biaya

### Rangkuman proses
1. Membentuk data MLC: 15.718 kasus lengkap pada 19 indikator konstruk dan variabel teramati (treatment, outcome, umur ibu, urutan lahir, dan confounder konteks DAG analisis).
2. Menetapkan jenis konstruk (N3 v2): komposit formatif eta_ekonomi, eta_akses; reflektif eta_pendidikan; reflektif yang dipecah karena ω < 0,7: eta_kebersihan.
3. Menghitung matriks korelasi respons laten berbobot survei: tetrakorik (biner–biner), biserial (biner–kontinu), Pearson berbobot (lainnya).
4. Mengestimasi model satu-faktor per konstruk dan memurnikan indikator dengan kendala tetrad di dalam dan lintas konstruk serta batas muatan 0,30: 0 indikator dibuang.
5. Menghitung kovarians antar-konstruk yang dikoreksi galat ukur, λ_dᵀ S_de λ_e / ((λ_dᵀλ_d)(λ_eᵀλ_e)), sehingga statistik cukup Σ̂_V hanya berukuran 19×19.
6. Menemukan DAG pada Σ̂_V (todag), lalu membandingkannya dengan ablasi tanpa konstruk (penemuan yang sama pada 32 node indikator mentah).
7. Menghitung efek dengan langkah estimasi bersama; konstruk dalam adjustment set diwakili skor faktor Bartlett.

### Narasi
Konstruk laten mengecilkan graf dari **32 menjadi 19 node** (statistik cukup 1.024 → 361 entri). Tahap penemuan struktur hanya 0,672 detik (2641 skor lokal) dibanding 2,132 detik (10179 skor lokal) tanpa konstruk; biaya terbesar justru korelasi tetrakorik (2,79 detik) yang dipakai bersama oleh keduanya. Graf yang ditemukan **tidak memuat jalur berarah dari T_pbi ke Y_diare**, sehingga efek kausal menurut graf ini nol.

Reliabilitas / jenis konstruk: eta_pendidikan=0,89, eta_kebersihan=0,32, eta_ekonomi=komposit (PC1 56%), eta_akses=komposit (PC1 45%). Aset dan akses diperlakukan sebagai indeks komposit karena indikatornya membentuk dimensi (formatif), bukan dicerminkan oleh satu faktor; konstruk reflektif hanya dipertahankan bila reliabilitasnya memadai.

**Perbandingan dengan baseline.** Dengan kriteria waktu penemuan, memori puncak, lebar CI, peringkat rata-rata terbaik diraih **B2 PC + tier + IDA** (1,33; unggul pada memori puncak, lebar CI); N3 MLC-DAG berada di urutan ke-4 dari 4 metode yang diperingkat (peringkat rata-rata 3,33). Efeknya nol menurut graf (tidak ada jalur berarah), sehingga tidak ada CI. Perbandingan pada data nyata tanpa ground truth bukan bukti keunggulan; klaim kandidat harus diuji pada evaluasi semi-sintetik.

## SOL-DAG — sanitasi_diare

### Rangkuman proses
1. Langkah 1 (MLC v2): konstruk reflektif eta_pendidikan; komposit formatif eta_ekonomi, eta_akses; konstruk yang dipecah menjadi indikator eta_kebersihan; kovarians Σ̂_V terkoreksi galat ukur (18 node).
2. Langkah 2 (SD-Hybrid): skeleton PC-stable dengan uji terkoreksi desain (Rao-Scott orde 2 / t-desain, α = 0,05); 11269 uji, 51 sisi.
3. Langkah 3 (TO-DAG): pencarian urutan di dalam tier dengan skor Gauss berskala n_eff = 2.356, induk dibatasi skeleton.
4. Langkah 4 (estimasi): PSU dibagi dua di dalam strata; graf ditemukan pada separuh A (7.728 kelahiran), AIPW berbobot survei pada separuh B (7.876), CI bootstrap PSU (500 replikasi).
5. Ablasi: mengulang pipeline dengan mematikan satu komponen (MLC, koreksi desain, tier, pemisahan sampel).
6. SOL v2 (pra-registrasi): graf PC-stable + tier dengan uji-t desain hanya memilih himpunan penyesuaian (induk T, ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU dan SE fungsi pengaruh + linearisasi desain.

### Narasi
SOL-DAG menemukan graf dengan 40 sisi pada 18 node dalam 20,4 detik (memori puncak 3,4 MB). Graf ini **tidak memuat jalur berarah dari T_sanitasi ke Y_diare**, sehingga efek sanitasi layak terhadap diare pada balita (2 minggu terakhir) menurut SOL-DAG adalah nol. Penyebabnya, uji terkoreksi desain menghapus sisi yang hanya lemah bermakna setelah dikondisikan pada variabel konteks; ini adalah kehilangan daya uji yang diantisipasi dokumen Tahap 3.

**Ablasi.** SOL tanpa MLC: 33 sisi, skeleton 37, RD 0,0000 (tanpa jalur T→Y); SOL tanpa koreksi desain: 53 sisi, skeleton 63, RD -0,0325; SOL tanpa tier: 38 sisi, skeleton 51, RD -0,0378; SOL tanpa pemisahan sampel: 54 sisi, skeleton 67, RD -0,0307. Perbedaan antar-varian menunjukkan kontribusi tiap komponen pada data nyata; uji formal H1–H5 dengan graf benar ada di menu Benchmark.

**SOL v2.** SOL v2 (desain): RD -0,0324 [-0,0544; -0,0104] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: sanitasi_klaster_lo, pend_ibu_thn, org_per_kamar, skor_kekayaan_nonwash, cuci_tangan_dasar; SOL v2 naif: RD -0,0326 [-0,0545; -0,0106] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: sanitasi_klaster_lo, pend_ibu_thn, org_per_kamar, skor_kekayaan_nonwash, air_layak, cuci_tangan_dasar; SOL v2 + MLC: RD -0,0309 [-0,0524; -0,0094] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: eta_pendidikan, eta_ekonomi, umur_ibu, sanitasi_klaster_lo, org_per_kamar. Berbeda dengan v1, efek tidak lagi dinolkan ketika graf tidak memuat jalur T→Y; graf hanya menentukan variabel yang dikontrol.

## SOL-DAG — pbi_diare

### Rangkuman proses
1. Langkah 1 (MLC v2): konstruk reflektif eta_pendidikan; komposit formatif eta_ekonomi, eta_akses; konstruk yang dipecah menjadi indikator eta_kebersihan; kovarians Σ̂_V terkoreksi galat ukur (19 node).
2. Langkah 2 (SD-Hybrid): skeleton PC-stable dengan uji terkoreksi desain (Rao-Scott orde 2 / t-desain, α = 0,05); 9084 uji, 52 sisi.
3. Langkah 3 (TO-DAG): pencarian urutan di dalam tier dengan skor Gauss berskala n_eff = 2.498, induk dibatasi skeleton.
4. Langkah 4 (estimasi): PSU dibagi dua di dalam strata; graf ditemukan pada separuh A (7.819 kelahiran), AIPW berbobot survei pada separuh B (7.899), CI bootstrap PSU (500 replikasi).
5. Ablasi: mengulang pipeline dengan mematikan satu komponen (MLC, koreksi desain, tier, pemisahan sampel).
6. SOL v2 (pra-registrasi): graf PC-stable + tier dengan uji-t desain hanya memilih himpunan penyesuaian (induk T, ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU dan SE fungsi pengaruh + linearisasi desain.

### Narasi
SOL-DAG menemukan graf dengan 47 sisi pada 19 node dalam 20,5 detik (memori puncak 3,7 MB). Graf ini **tidak memuat jalur berarah dari T_pbi ke Y_diare**, sehingga efek kepesertaan JKN PBI terhadap diare pada balita (2 minggu terakhir) menurut SOL-DAG adalah nol. Penyebabnya, uji terkoreksi desain menghapus sisi yang hanya lemah bermakna setelah dikondisikan pada variabel konteks; ini adalah kehilangan daya uji yang diantisipasi dokumen Tahap 3.

**Ablasi.** SOL tanpa MLC: 25 sisi, skeleton 29, RD 0,0000 (tanpa jalur T→Y); SOL tanpa koreksi desain: 51 sisi, skeleton 55, RD 0,0179; SOL tanpa tier: 45 sisi, skeleton 52, RD 0,0202; SOL tanpa pemisahan sampel: 54 sisi, skeleton 64, RD 0,0000 (tanpa jalur T→Y). Perbedaan antar-varian menunjukkan kontribusi tiap komponen pada data nyata; uji formal H1–H5 dengan graf benar ada di menu Benchmark.

**SOL v2.** SOL v2 (desain): RD 0,0252 [0,0079; 0,0426] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: pbi_pct_prov, ibu_bekerja, jml_art, pend_ibu_thn, skor_kekayaan_nonwash, T_sanitasi; SOL v2 naif: RD 0,0252 [0,0079; 0,0426] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: pbi_pct_prov, ibu_bekerja, jml_art, pend_ibu_thn, skor_kekayaan_nonwash, T_sanitasi; SOL v2 + MLC: RD 0,0270 [0,0092; 0,0448] (bermakna secara statistik (CI 95% tidak memuat nol)), induk T: eta_pendidikan, eta_ekonomi, urutan_lahir, pbi_pct_prov, jml_art. Berbeda dengan v1, efek tidak lagi dinolkan ketika graf tidak memuat jalur T→Y; graf hanya menentukan variabel yang dikontrol.

## SOL-DAG — pbi_neonatal

### Rangkuman proses
1. Langkah 1 (MLC v2): konstruk reflektif eta_pendidikan; komposit formatif eta_ekonomi, eta_akses; konstruk yang dipecah menjadi indikator eta_kebersihan; kovarians Σ̂_V terkoreksi galat ukur (17 node).
2. Langkah 2 (SD-Hybrid): skeleton PC-stable dengan uji terkoreksi desain (Rao-Scott orde 2 / t-desain, α = 0,05); 4493 uji, 40 sisi.
3. Langkah 3 (TO-DAG): pencarian urutan di dalam tier dengan skor Gauss berskala n_eff = 1.547, induk dibatasi skeleton.
4. Langkah 4 (estimasi): PSU dibagi dua di dalam strata; graf ditemukan pada separuh A (3.182 kelahiran), AIPW berbobot survei pada separuh B (3.203), CI bootstrap PSU (500 replikasi).
5. Ablasi: mengulang pipeline dengan mematikan satu komponen (MLC, koreksi desain, tier, pemisahan sampel).
6. SOL v2 (pra-registrasi): graf PC-stable + tier dengan uji-t desain hanya memilih himpunan penyesuaian (induk T, ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU dan SE fungsi pengaruh + linearisasi desain.

### Narasi
SOL-DAG menemukan graf dengan 36 sisi pada 17 node dalam 8,3 detik (memori puncak 1,6 MB). Graf ini **tidak memuat jalur berarah dari T_pbi ke Y_mati_neonatal**, sehingga efek kepesertaan JKN PBI terhadap kematian neonatal menurut SOL-DAG adalah nol. Penyebabnya, uji terkoreksi desain menghapus sisi yang hanya lemah bermakna setelah dikondisikan pada variabel konteks; ini adalah kehilangan daya uji yang diantisipasi dokumen Tahap 3.

**Ablasi.** SOL tanpa MLC: 18 sisi, skeleton 21, RD 0,0000 (tanpa jalur T→Y); SOL tanpa koreksi desain: 44 sisi, skeleton 48, RD 0,0000 (tanpa jalur T→Y); SOL tanpa tier: 37 sisi, skeleton 40, RD 0,0000 (tanpa jalur T→Y); SOL tanpa pemisahan sampel: 42 sisi, skeleton 49, RD 0,0000 (tanpa jalur T→Y). Perbedaan antar-varian menunjukkan kontribusi tiap komponen pada data nyata; uji formal H1–H5 dengan graf benar ada di menu Benchmark.

**SOL v2.** SOL v2 (desain): RD -0,0017 [-0,0081; 0,0047] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: pbi_pct_prov, jml_art, pend_ibu_thn, skor_kekayaan_nonwash; SOL v2 naif: RD -0,0017 [-0,0081; 0,0047] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: pbi_pct_prov, jml_art, pend_ibu_thn, skor_kekayaan_nonwash; SOL v2 + MLC: RD -0,0004 [-0,0073; 0,0064] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: eta_pendidikan, eta_ekonomi, pbi_pct_prov, jml_art. Berbeda dengan v1, efek tidak lagi dinolkan ketika graf tidak memuat jalur T→Y; graf hanya menentukan variabel yang dikontrol.

## SOL-DAG — fasilitas_neonatal

### Rangkuman proses
1. Langkah 1 (MLC v2): konstruk reflektif eta_pendidikan; komposit formatif eta_ekonomi, eta_akses; konstruk yang dipecah menjadi indikator eta_kebersihan; kovarians Σ̂_V terkoreksi galat ukur (16 node).
2. Langkah 2 (SD-Hybrid): skeleton PC-stable dengan uji terkoreksi desain (Rao-Scott orde 2 / t-desain, α = 0,05); 6300 uji, 38 sisi.
3. Langkah 3 (TO-DAG): pencarian urutan di dalam tier dengan skor Gauss berskala n_eff = 2.258, induk dibatasi skeleton.
4. Langkah 4 (estimasi): PSU dibagi dua di dalam strata; graf ditemukan pada separuh A (8.011 kelahiran), AIPW berbobot survei pada separuh B (8.147), CI bootstrap PSU (500 replikasi).
5. Ablasi: mengulang pipeline dengan mematikan satu komponen (MLC, koreksi desain, tier, pemisahan sampel).
6. SOL v2 (pra-registrasi): graf PC-stable + tier dengan uji-t desain hanya memilih himpunan penyesuaian (induk T, ala IDA); efek selalu diestimasi dengan AIPW cross-fitting per PSU dan SE fungsi pengaruh + linearisasi desain.

### Narasi
SOL-DAG menemukan graf dengan 34 sisi pada 16 node dalam 12,8 detik (memori puncak 3,3 MB). Graf ini **tidak memuat jalur berarah dari T_fasilitas ke Y_mati_neonatal**, sehingga efek persalinan di fasilitas kesehatan terhadap kematian neonatal menurut SOL-DAG adalah nol. Penyebabnya, uji terkoreksi desain menghapus sisi yang hanya lemah bermakna setelah dikondisikan pada variabel konteks; ini adalah kehilangan daya uji yang diantisipasi dokumen Tahap 3.

**Ablasi.** SOL tanpa MLC: 28 sisi, skeleton 32, RD 0,0000 (tanpa jalur T→Y); SOL tanpa koreksi desain: 43 sisi, skeleton 49, RD 0,0000 (tanpa jalur T→Y); SOL tanpa tier: 34 sisi, skeleton 38, RD 0,0000 (tanpa jalur T→Y); SOL tanpa pemisahan sampel: 39 sisi, skeleton 47, RD 0,0000 (tanpa jalur T→Y). Perbedaan antar-varian menunjukkan kontribusi tiap komponen pada data nyata; uji formal H1–H5 dengan graf benar ada di menu Benchmark.

**SOL v2.** SOL v2 (desain): RD -0,0019 [-0,0097; 0,0059] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: fasilitas_klaster_lo, pend_ibu_thn, urutan_lahir, skor_kekayaan_nonwash; SOL v2 naif: RD -0,0019 [-0,0097; 0,0059] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: fasilitas_klaster_lo, pend_ibu_thn, urutan_lahir, skor_kekayaan_nonwash; SOL v2 + MLC: RD -0,0026 [-0,0105; 0,0053] (tidak bermakna secara statistik (CI 95% memuat nol)), induk T: eta_pendidikan, eta_ekonomi, cuci_tangan_dasar, air_layak, urutan_lahir, perdesaan, fasilitas_klaster_lo. Berbeda dengan v1, efek tidak lagi dinolkan ketika graf tidak memuat jalur T→Y; graf hanya menentukan variabel yang dikontrol.

## Benchmark semi-sintetik — sanitasi_diare

### Rangkuman proses
1. Skenario A: graf benar = DAG pakar sanitasi_diare dengan 30% panah diganti (patuh tier); SCM dicocokkan pada IDHS (logistik/linear berbobot) dengan efek acak PSU dari ANOVA residual.
2. Skenario B: node = konstruk/komposit MLC v2 dan variabel teramati; graf benar = DAG pakar dipetakan ke tingkat konstruk lalu diperturbasi; indikator dibangkitkan dari konstruknya (muatan nyata, ambang prevalensi).
3. Setiap skenario diulang 100 kali dengan bobot, PSU, dan strata IDHS asli; efek benar dihitung secara kontrafaktual do(T=1) − do(T=0) dengan noise bersama.
4. Metrik yang sama untuk semua metode: SHD, SID, |galat RD| (RMSE), waktu dan memori penemuan, stabilitas (SHD antar-replikasi), cakupan CI 95% (20 bootstrap PSU), galat tipe I dan daya uji pada 20 pernyataan independensi/dependensi benar.
5. Uji hipotesis: SOL-DAG vs setiap pembanding dengan Wilcoxon berpasangan satu sisi, p dikoreksi Holm per hipotesis; H5 dengan interval Wilson terhadap target nominal.
6. Benchmark v2 (pra-registrasi): DAG acak patuh tier yang independen dari metode, grid ICC {0,05; 0,4} × β_TY {−0,6; −0,15; 0}, 200 replikasi per sel; varian v2 desain, v2 naif, dan aturan v1.
7. Benchmark v3 (pra-registrasi S6–S10): desain sintetis setara IDHS (67 strata × 29 PSU × 9), ICC heterogen U(0,1; 0,8) vs homogen 0,45; lima uji CI (naif, Kish, deff-global, sandwich CR1, desain usulan); S8 200 replikasi, dampak hilir 100 replikasi (p = 15 utama, 30 sekunder).

### Narasi
**Skenario A.** Efek benar RD = -0,0202 (14,1% vs 16,2%); graf benar 29 sisi. SHD terkecil: B3 BN skor (14,7); RMSE efek terkecil: B2 PC + tier + IDA (0,0090). SOL-DAG: SHD 16,9, SID 76,2, RMSE 0,0197, efek nol pada 93% replikasi, cakupan CI 6%.

**Skenario B.** Efek benar RD = -0,0455 (13,0% vs 17,5%); graf benar 29 sisi. SHD terkecil: SOL-DAG (14,1); RMSE efek terkecil: N3 MLC-DAG (0,0104). SOL-DAG: SHD 14,1, SID 79,7, RMSE 0,0263, efek nol pada 10% replikasi, cakupan CI 75%.

**Putusan hipotesis.** H1 (Akurasi): **didukung sebagian** (4/27); H2 (Kecepatan): **didukung sebagian** (3/8); H3 (Memori): **didukung sebagian** (7/8); H4 (Konvergensi & stabilitas): **didukung sebagian** (6/8); H5 (Validitas koreksi desain): **didukung sebagian** (1/2).

**H5 — validitas koreksi desain.** Pada pernyataan independensi yang benar, uji naif menolak 12,8% (CI 11,4–14,3%) dan uji terkoreksi 4,5% (CI 3,6–5,4%) terhadap nominal 5%.

Benchmark ini memakai satu analisis dan satu graf benar per skenario; kesimpulan umum memerlukan variasi graf, ukuran efek, dan kekuatan klaster.

**Benchmark v2 (pra-registrasi).** H1v2 (Estimasi sadar-query memulihkan efek): **diterima** — ICC 0.05 β -0.15: cakupan 92.5%, efek nol 0.0%; ICC 0.05 β -0.6: cakupan 92.5%, efek nol 0.0%; ICC 0.4 β -0.15: cakupan 91.0%, efek nol 0.0%; ICC 0.4 β -0.6: cakupan 93.0%, efek nol 0.0%; H2v2 (v2 lebih akurat daripada aturan v1 pada efek kecil): **gagal** — ICC 0.05: RMSE v2 0.0300 vs v1 0.0318 (lebih kecil) (p Holm 3.4e-09); ICC 0.4: RMSE v2 0.0341 vs v1 0.0307 (TIDAK lebih kecil) (p Holm 0.00049); H3v2 (Uji desain terkalibrasi (ICC 0,4)): **diterima** — galat tipe I desain 5.7% (Wilson 5.3%–6.1%, n≈12000); H4v2 (Uji naif tidak terkalibrasi (ICC 0,4)): **diterima** — galat tipe I naif 14.1%; H5v2 (Kehilangan daya uji terbatas): **diterima** — daya desain 82.0% vs naif 84.1% (selisih -2.1 pp, semua sel); H6v2 (Akurasi struktur tidak lebih buruk (ICC 0,4)): **diterima** — SHD desain 6.14 vs naif 6.07 (selisih +0.07).

**Benchmark v3 (pra-registrasi).** H8a (Uji desain terkalibrasi pada deff heterogen): **diterima** — galat tipe I 5.2% (Wilson 4.7%–5.7%); H8b (Pembanding lazim salah kalibrasi): **diterima** — naif 18.2%, Kish 18.4% (> 10%?); deff-global 0.4% (< 2,5%?); H8c (Uji desain setara sandwich CR1): **diterima → klaim 'uji baru' DICABUT** — kesepakatan keputusan pada H0 99.9% (heterogen 99.9%; homogen 99.9%); H8d (Daya uji desain > deff-global): **diterima** — daya desain 54.3% vs deff-global 43.4% (selisih +10.8 pp); H7a (Validitas himpunan penyesuaian desain ≥ naif dan Kish (heterogen)): **gagal** — desain 72.0% vs naif 90.0% (p Holm 1), Kish 84.0% (p Holm 1); H7b (FDR sisi desain < naif): **diterima** — heterogen: 0.072 vs 0.191 (p Holm 7.8e-10); homogen: 0.052 vs 0.167 (p Holm 7.8e-10); H9 (Cakupan CI (uji desain, p = 15)): **diterima** — heterogen: gabungan 100.0%, utama 100.0%; homogen: gabungan 98.0%, utama 98.0%. Tafsiran bagian ambigu: H8a, H8b, H8d pada skenario heterogen (inti S8); H8c gabungan kedua skenario; H7a heterogen seperti tertulis; H7b dan H9 memakai skenario heterogen sebagai utama (homogen dilaporkan); H9 pada uji desain_usulan, p = 15.

## Benchmark v4 — pemilihan confounder M0–M6

### Rangkuman proses
1. Setiap replikasi membangkitkan graf acak patuh tier (15 atau 30 node): kovariat di tier 0–2, treatment biner T di tier 3, outcome biner Y di tier 4; tiga kovariat dipaksa menjadi confounder (kuat: koefisien 0,30–0,50; lemah: 0,05–0,15) dan 15% kovariat lain disembunyikan dari metode.
2. Data dibangkitkan pada desain sintetis setara IDHS (67 strata × 29 PSU × 9 unit) dengan efek acak PSU per variabel (ICC heterogen U(0,1; 0,8) atau 0,15); efek benar dihitung eksak dari model probit.
3. Tujuh strategi memilih himpunan penyesuaian: M0 semua kovariat pra-treatment; M1 induk T di DAG pakar yang 30% panahnya keliru; M2 PC naif; M3 PC dengan uji terkoreksi desain; M4 = M3 dengan α longgar (0,10, 0,20, 0,30) untuk pasangan yang melibatkan T atau Y; M5 induk T dari M3 ∪ M1; M6 induk T atau induk Y dari graf M3.
4. Semua strategi memakai estimator yang sama: AIPW cross-fitting 5 lipatan per PSU, SE linearisasi desain, sehingga perbedaan hasil hanya berasal dari himpunan penyesuaian.
5. Grid 24 sel (ICC × efek × kekuatan confounder × jumlah node), 200 replikasi per sel = 4.800 survei simulasi. Ukuran: validitas himpunan penyesuaian di graf benar, FDR skeleton, RMSE, dan cakupan CI 95%.
6. Hipotesis H10–H13 dan cara membacanya dikunci sebelum simulasi penuh (RENCANA_ANALISIS_v4.md, tag git rencana-v4) dan diuji pada sel ICC heterogen.

### Narasi
**Kalibrasi melawan identifikasi.** Koreksi desain memperbaiki graf: FDR skeleton turun dari 27,1% (M2, uji naif) menjadi 13,4% (M3, uji terkoreksi). Namun himpunan penyesuaian yang valid justru turun dari 55,0% menjadi 49,2%, dan RMSE naik dari 0,0136 menjadi 0,0142. Uji yang ukurannya benar lebih sulit mendeteksi sisi confounder yang lemah, sehingga graf yang lebih baik menghasilkan himpunan penyesuaian yang lebih buruk.

**Melonggarkan α (M4) hanya memulihkan sebagian.** Validitas naik dari 51,8% pada α_T = 0,10 menjadi 58,2% pada 0,30, dengan FDR tetap 14,0%–16,5%. Memperbesar himpunan lebih efektif: M5 mencapai 69,8% dan M6 77,2%.

**Dua acuan.** M0 (semua kovariat pra-treatment) valid pada 99,2% replikasi dengan RMSE 0,0098 dan cakupan 94,4%, memakai rata-rata 17,5 kovariat (M6: 9,6). M1 (DAG pakar yang 30% keliru) adalah pilihan terburuk: valid 14,2%, RMSE 0,0487, cakupan 56,3%.

**Kekuatan confounder menentukan.** Pada semua sel, validitas dengan confounder kuat adalah 73,3% (M2), 72,0% (M3), dan 95,3% (M6); dengan confounder lemah turun menjadi 38,6%, 31,5%, dan 65,0%. Untuk M2–M4, RMSE 0,0103 bila himpunannya valid dan 0,0159 bila tidak; cakupan 94,3% dan 86,8%.

**Putusan hipotesis.** H10: **ditolak** — M6 77.2% (Wilson 75.5%-78.8%) vs M2 55.0%, M0 99.2%; H11: **diterima** — 0.140 vs 0.271 (Wilcoxon p 0); H12: **ditolak** — M6 0.0099 vs M0 0.0098 (Wilcoxon |galat| p 0.086); H13: **diterima** — M6 94.0%. H10 ditolak, sehingga sesuai rencana hasil ini dibaca sebagai peringatan: penemuan graf dengan uji terkalibrasi belum dapat diandalkan untuk memilih confounder. H12 ditolak hanya pada nilai titik; M6 dan M0 praktis setara dalam ketepatan.

**M0–M6 pada IDHS 2017.** sanitasi layak → diare pada balita (2 minggu terakhir): RD -0,0326 sampai -0,0299 di ketujuh strategi (n = 16.232), semua CI 95% tidak memuat nol; kepesertaan JKN PBI → diare pada balita (2 minggu terakhir): RD 0,0235 sampai 0,0266 di ketujuh strategi (n = 16.508), semua CI 95% tidak memuat nol. Efek benar tidak diketahui pada data nyata; yang dibaca adalah konsistensi antar-himpunan, bukan peringkat metode. Arah positif pada JKN PBI mencerminkan confounding penargetan, bukan bukti bahaya.

Keterbatasan: graf simulasi tidak memuat mediator antara T dan Y, sehingga M0 aman secara konstruksi; efek laten linear, satu desain sampling, dan satu algoritma penemuan (PC-stable).
