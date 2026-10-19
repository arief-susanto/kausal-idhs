# Kausal IDHS

Pipeline Python berbasis konfigurasi dengan antarmuka Streamlit untuk analisis kausal data Survei Demografi dan
Kesehatan Indonesia (SDKI/IDHS) 2017 yang memperhitungkan desain survei: DAG dan identifikasi, estimator g-komputasi,
IPW, dan AIPW dengan galat baku desain, penemuan graf kausal dengan uji yang dikoreksi desain, pemilihan perancu
M0–M6, serta benchmark simulasi dengan graf benar yang diketahui.

**Lihat luaran aplikasi tanpa memasang apa pun: [LUARAN.md](LUARAN.md).**

> **Data tidak disertakan.** Mikrodata SDKI 2017 tidak boleh dibagikan ulang (lisensi The DHS Program). Ajukan akses di
> https://dhsprogram.com, lalu taruh `IDBR71DT.zip` dan `IDHR71DT.zip` di `data_mentah/`. Folder `luaran/` hanya berisi
> hasil agregat. Benchmark simulasi (`bench_v4.py`, `v2/`, `v3/`) dapat dijalankan tanpa data DHS.

Penulis: Arief Susanto, Aris Puji Widodo, Adi Wibowo (Universitas Diponegoro; Universitas Muria Kudus).
Lisensi: MIT. Cara mengutip: lihat [CITATION.cff](CITATION.cff).

---

# Pipeline kausal IDHS 2017 (sanitasi, JKN PBI, persalinan di fasilitas)

## Reproduksi naskah jurnal (versi `v-paper1`)
Semua angka dan gambar naskah berasal dari satu versi kode: tag `v-paper1`,
commit `b077acea04f12382a0cb1d18b0fe4026dd5fe611` (lihat `naskah_commit.txt`).
Rencana analisis benchmark dikunci sebelum simulasi penuh dijalankan: `RENCANA_ANALISIS_v4.md`, tag `rencana-v4`,
commit `91edfd767c8d2adbd67a20ea61d17f10b306039a`.

**Data tidak disertakan.** Data IDHS 2017 tidak boleh dibagikan ulang. Daftar dan ajukan permintaan di
https://dhsprogram.com (Indonesia DHS 2017, Births Recode dan Household Recode), lalu taruh `IDBR71DT.zip` dan
`IDHR71DT.zip` tanpa diekstrak di folder `data_mentah/`. Benchmark simulasi (`bench_v4.py`) tidak membutuhkan data ini.

Urutan menjalankan (Python >= 3.10, pustaka di `requirements-lock.txt`):

    python main.py prep                         # Persiapan Data -> cache/analisis.pkl
    python main.py baseline sanitasi_diare      # Baseline B1-B3 (ulangi untuk pbi_diare dan dua analisis sensitivitas)
    python main.py kausal sanitasi_diare        # Inferensi Kausal: g-komputasi, IPW, AIPW, bootstrap PSU
    python main.py sol_v2 sanitasi_diare        # SOL v2
    python main.py sd_hybrid sanitasi_diare     # N1 + simulasi galat tipe I (gambar G3)
    python idhs_m0m6.py                         # M0-M6 pada IDHS (forest plot G5)
    python -u bench_v4.py                       # benchmark v4: 200 replikasi x 24 sel, ~14 jam dengan 4 pekerja
    python naskah_bahan.py                      # kumpulkan gambar dan tabel ke naskah/

Analisis naskah: `sanitasi_diare` (utama), `pbi_diare` (contoh peringatan), dan sensitivitas mediator
`sanitasi_diare_ctps`, `pbi_diare_biaya`. Ringkasan hasil yang ikut repositori ada di `ringkasan/` dan `naskah/tabel/`;
folder `hasil/` tidak ikut karena dibuat ulang oleh perintah di atas.

## Pasang sekali
    pip install -r requirements.txt
Taruh `IDBR71DT.zip` dan `IDHR71DT.zip` (dari DHS, tanpa diekstrak) di folder `data_mentah/`.

## Jalankan
    python main.py                 # buka tampilan di browser (atau klik ganda jalankan_app.bat)
Menu di sidebar kiri: Persiapan Data, EDA, Inferensi Kausal, Baseline (B1–B3), N1 SD-Hybrid, N2 TO-DAG, N3 MLC-DAG, SOL-DAG, Benchmark (H1–H5), dan tombol Jalankan semua.
Setiap menu novelty punya submenu **Perbandingan dengan baseline** (jalankan menu Baseline lebih dulu).
Laporan Word bernama sesuai menu (Laporan_Persiapan_Data, Laporan_EDA, Laporan_Inferensi_Kausal, Laporan_Baseline_B1-B3, Laporan_N1_SD-Hybrid, Laporan_N2_TO-DAG, Laporan_N3_MLC-DAG) diunduh dari pojok kanan atas tiap menu; Laporan_Lengkap_Semua_Menu dari sidebar.
Setiap menu menampilkan panel **📝 Rangkuman proses & narasi** yang dibuat otomatis dari hasil terakhir.
Proses, tabel, dan grafik tampil di kanan. Program otomatis memakai Python dari .venv.

Tanpa tampilan (mis. untuk run panjang bootstrap 1000):
    python main.py semua           # prep -> EDA -> kausal
    python main.py kausal sanitasi_diare   # satu analisis saja
    python main.py dag             # cek DAG & identifikasi saja (cepat, tanpa data)
    python main.py baseline        # B1 SEM, B2 PC+tier+IDA, B3 BN skor (semua analisis)
    python main.py sd_hybrid       # N1 (juga to_dag, mlc_dag); tambahkan nama analisis bila perlu
    python main.py sol             # SOL-DAG terintegrasi + 4 ablasi (semua analisis)
    python main.py benchmark sanitasi_diare   # benchmark semi-sintetik H1-H5 (paralel, ±2 jam untuk 100 replikasi)
    python main.py laporan         # laporan Word per menu + lengkap di hasil/laporan/
    python main.py narasi          # tulis rangkuman proses & narasi seluruh menu ke hasil/NARASI.md

## Struktur (edit hanya config.py)
| File | Isi |
|---|---|
| config.py | Lokasi file, jumlah bootstrap, DAG tiap analisis |
| prep.py | Menu 1: data mentah -> cache/analisis.pkl (+ hasil/dataset_analisis.csv) |
| eda.py | Menu 2: deskriptif berbobot + SE desain, SMD, per kuintil/provinsi, grafik |
| causal.py | Menu 3: DAG -> adjustment set backdoor -> g-komputasi, IPW, AIPW, bootstrap PSU, E-value |
| baseline.py | Menu 4: baseline pembanding SOL-DAG: B1 DAG pakar + SEM, B2 PC-stable + tier + IDA, B3 BN skor + do |
| novelty.py | Menu N1-N3: SD-Hybrid (uji Rao-Scott/t-desain + skor berbobot), TO-DAG (pencarian urutan dalam tier), MLC-DAG (konstruk laten + purifikasi tetrad) |
| laporan.py | Laporan Word (.docx) menu Baseline dan N1–N3: tabel, grafik, uji galat tipe I, rangkuman proses, narasi |
| sol_dag.py | Menu SOL-DAG: MLC v2 -> skeleton terkoreksi desain -> TO-DAG -> AIPW dengan pemisahan sampel per PSU, + ablasi |
| benchmark.py | Menu Benchmark: SCM semi-sintetik dari IDHS (graf benar diketahui, desain klaster dipertahankan), SHD/SID/RMSE/cakupan/galat uji, uji H1-H5 |
| narasi.py | Rangkuman proses & narasi otomatis (Bahasa Indonesia) untuk setiap menu |
| app.py | Tampilan Streamlit (menu kiri, proses kanan) |
| main.py | Pembuka tampilan + perintah tanpa tampilan + log ringkasan |

## Keluaran
Salinan agregat luaran ada di `luaran/` (lihat [LUARAN.md](LUARAN.md)); saat dijalankan, aplikasi menulis ke `hasil/`.
- `hasil/RINGKASAN.txt`: ringkasan beberapa baris per langkah. **Tempelkan file ini saja** saat berdiskusi dengan AI atau pembimbing.
- `hasil/eda/`: tabel CSV dan grafik PNG.
- `hasil/kausal/<analisis>/`: dag.png, adjustment.txt, estimasi.csv, keseimbangan.csv, overlap.png.
- `hasil/baseline/<analisis>/`: rangkuman.csv (metode terbaik: peringkat rata-rata BIC-SEM, CFI, lebar CI), perbandingan.csv/.png, b1_* (kecocokan, koefisien, dekomposisi), b2_* (cpdag, ida), b3_* (dag, jejak skor). Tier variabel di `config.TIER`, pengaturan di `config.BASELINE`.
- `hasil/sol_dag/<analisis>/`: sol_varian.csv (SOL + ablasi), sol_banding.csv/.png, graf SOL-DAG.
- `hasil/benchmark/<analisis>/`: per_rep.csv, ringkasan.csv, hipotesis.csv, hipotesis_H5.csv, putusan.csv, graf benar A/B. Pengaturan di `config.BENCH`.
- `hasil/novelty/<metode>/<analisis>/`: banding.csv/.png (perbandingan dengan B1–B3), graf, info, plus sd_tipe1.csv (simulasi galat tipe I), to_jejak.csv (konvergensi), mlc_muatan.csv & mlc_purifikasi.csv (model pengukuran). Pengaturan di `config.NOVELTY`, konstruk di `config.MLC_KONSTRUK`.

## Menambah atau mengubah analisis
Salin satu blok di `ANALISIS` pada config.py, lalu ganti `T`, `Y`, `filter`, `edges`, `laten`.
Program otomatis menghitung adjustment set, memeriksa identifikasi (kriteria backdoor), dan
memberi tahu jika ada variabel laten yang membuat efek tidak teridentifikasi.

## Cara membaca hasil
- identifikasi=TIDAK: DAG Anda menyatakan ada confounder tak terukur, sehingga estimasi berisiko bias. Laporkan E-value.
- AIPW adalah estimator utama (doubly robust). g-komputasi dan IPW berfungsi sebagai uji sensitivitas; selisih besar di antara ketiganya menandakan spesifikasi model bermasalah.
- SMD maks setelah IPW sebaiknya < 0,1.
- E-value: seberapa kuat confounder tak terukur (dalam skala risk ratio) yang dibutuhkan untuk menghapus efek.
- BOOT=200 untuk eksplorasi; gunakan 1000 untuk hasil final disertasi.
