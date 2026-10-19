"""KONFIGURASI TUNGGAL. Ubah analisis cukup di file ini, tidak perlu menyentuh kode lain.

VERSI AUDIT (v-paper1, 10-10-2026). Baris bertanda  # AUDIT:  = diubah atau perlu keputusan Anda.
Perubahan nilai hanya pada parameter yang sudah dibaca kode; tidak ada kunci baru.
"""
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data_mentah"            # taruh IDBR71DT.zip dan IDHR71DT.zip di sini
KONTEKS = ROOT / "data_konteks" / "konteks_provinsi_2017.csv"
CACHE = ROOT / "cache"                # hasil ekstraksi/antara (otomatis)
OUT = ROOT / "hasil"                  # semua keluaran
SEED = 2017
BOOT = 500          # AUDIT: 200 -> 500 untuk hasil final (MC error CI lebih kecil)
TRIM = (0.01, 0.99) # pemangkasan propensity score

# ---------------------------------------------------------------------------
# DAG per analisis. Tulis panah sebagai "A -> B". Node yang tidak terukur
# dimasukkan ke 'laten' agar program memeriksa apakah efeknya tetap teridentifikasi.
# Setiap panah WAJIB punya rujukan literatur di disertasi.
# ---------------------------------------------------------------------------
_SOSEK = ["skor_kekayaan_nonwash -> {T}", "pend_ibu_thn -> {T}", "perdesaan -> {T}",
          "skor_kekayaan_nonwash -> {Y}", "pend_ibu_thn -> {Y}", "perdesaan -> {Y}",
          "pend_ibu_thn -> skor_kekayaan_nonwash", "perdesaan -> skor_kekayaan_nonwash",
          "p0_daerah_mar2017 -> {T}", "p0_daerah_mar2017 -> skor_kekayaan_nonwash"]

ANALISIS = {
    "sanitasi_diare": dict(
        T="T_sanitasi", Y="Y_diare", filter=None,
        # AUDIT: cuci tangan sebagai confounder vs mediator. STBM memuat pilar CTPS (cuci tangan pakai
        # sabun), jadi "{T} -> cuci_tangan_dasar" masuk akal. Jalankan KEDUA versi sebagai analisis
        # sensitivitas dan laporkan keduanya di naskah.
        edges=_SOSEK + [
            "{T} -> {Y}",
            "skor_kekayaan_nonwash -> cuci_tangan_dasar", "pend_ibu_thn -> cuci_tangan_dasar",
            "cuci_tangan_dasar -> {Y}", "sanitasi_klaster_lo -> {T}", "sanitasi_klaster_lo -> {Y}",
            "perdesaan -> sanitasi_klaster_lo", "air_layak -> {Y}", "skor_kekayaan_nonwash -> air_layak",
            "perdesaan -> air_layak", "olah_air_efektif -> {Y}", "pend_ibu_thn -> olah_air_efektif",
            "punya_ternak -> {Y}", "perdesaan -> punya_ternak", "org_per_kamar -> {Y}",
            "skor_kekayaan_nonwash -> org_per_kamar", "umur_anak_bln -> {Y}", "anak_laki -> {Y}",
            # ASUMSI: cuci tangan = confounder (dipengaruhi faktor yg sama dg sanitasi).
            # Jika program sanitasi Anda juga menyediakan sarana cuci tangan, ganti dengan:
            # "{T} -> cuci_tangan_dasar"  (maka cuci tangan menjadi mediator & otomatis tidak dikontrol)
            "cuci_tangan_klaster_lo -> cuci_tangan_dasar",
        ], laten=[]),

    # AUDIT: hambatan_biaya diperlakukan sebagai confounder, padahal PBI (JKN gratis) masuk akal
    # MENURUNKAN hambatan biaya -> hambatan_biaya bisa mediator. Bila disetujui, ganti
    # "skor_kekayaan_nonwash -> hambatan_biaya" + "hambatan_biaya -> {Y}" dengan menambah
    # "{T} -> hambatan_biaya", dan pindahkan hambatan_biaya ke tier 3 (lihat TIER).
    # AUDIT: T_pbi = status saat wawancara (v481c). Untuk diare 2 minggu terakhir urutan waktu masih
    # masuk akal; tafsirkan hasilnya sebagai contoh peringatan (confounding penargetan), bukan efek kausal.
    "pbi_diare": dict(
        T="T_pbi", Y="Y_diare", filter=None,
        edges=_SOSEK + [
            "{T} -> {Y}", "hambatan_biaya -> {Y}", "skor_kekayaan_nonwash -> hambatan_biaya",
            "pbi_pct_prov -> {T}", "kk_perempuan -> {T}", "jml_art -> {T}", "ibu_bekerja -> {T}",
            "pend_ibu_thn -> ibu_bekerja", "T_sanitasi -> {Y}", "skor_kekayaan_nonwash -> T_sanitasi",
            "air_layak -> {Y}", "skor_kekayaan_nonwash -> air_layak", "umur_anak_bln -> {Y}",
            "anak_laki -> {Y}", "jml_art -> {Y}",
        ], laten=[]),

    # PBI -> kematian neonatal: dibatasi ke kelahiran <24 bulan agar status PBI (diukur 2017)
    # lebih mungkin mendahului persalinan.
    # AUDIT: filter ini tidak menjamin urutan waktu; panah "{T} -> T_fasilitas" tetap bisa terbalik.
    # Keluarkan analisis ini dari naskah jurnal (simpan untuk disertasi dengan catatan keterbatasan).
    "pbi_neonatal": dict(
        T="T_pbi", Y="Y_mati_neonatal", filter="umur_anak_bln < 24",
        edges=_SOSEK + [
            "{T} -> T_fasilitas", "T_fasilitas -> {Y}", "{T} -> {Y}",
            "pbi_pct_prov -> {T}", "kk_perempuan -> {T}", "jml_art -> {T}",
            "umur_ibu -> {Y}", "urutan_lahir -> {Y}", "kembar -> {Y}", "umur_ibu -> urutan_lahir",
        ], laten=[]),

    "fasilitas_neonatal": dict(
        T="T_fasilitas", Y="Y_mati_neonatal", filter=None,
        edges=_SOSEK + [
            "{T} -> {Y}", "hambatan_jarak -> {T}", "hambatan_biaya -> {T}",
            "skor_kekayaan_nonwash -> hambatan_biaya", "perdesaan -> hambatan_jarak",
            "jarak_klaster_lo -> {T}", "fasilitas_klaster_lo -> {T}", "perdesaan -> fasilitas_klaster_lo",
            "rasio_pkm_per_kec -> fasilitas_klaster_lo", "pct_pkm_kurang_bidan -> {T}",
            "umur_ibu -> {T}", "umur_ibu -> {Y}", "urutan_lahir -> {T}", "urutan_lahir -> {Y}",
            "umur_ibu -> urutan_lahir", "kembar -> {T}", "kembar -> {Y}", "anak_laki -> {Y}",
            # Risiko kehamilan tidak terukur -> mendorong rujukan ke fasilitas & menaikkan kematian.
            "risiko_kehamilan -> {T}", "risiko_kehamilan -> {Y}",
        ], laten=["risiko_kehamilan"]),
    # AUDIT: tidak teridentifikasi (laten). Keluarkan dari naskah jurnal.
}

# ---------------------------------------------------------------------------
# BASELINE (menu 4): tier waktu tau(v). Panah i -> j dilarang jika tier(i) > tier(j).
# Setiap variabel di DAG analisis wajib punya tier.
# ---------------------------------------------------------------------------
# AUDIT: kekayaan, hambatan_biaya/jarak, dan PBI diukur saat wawancara 2017, sedangkan persalinan dan
# kematian neonatal bisa terjadi hingga 5 tahun sebelumnya. Tier di bawah tidak mencerminkan urutan
# waktu sebenarnya untuk outcome kelahiran -> tulis sebagai keterbatasan.
# AUDIT: hambatan_biaya (tier 2) dan hambatan_jarak (tier 3) berasal dari jenis pertanyaan yang sama;
# samakan tier-nya (usul: keduanya 3).
TIER_NAMA = ["konteks", "demografi", "ekonomi", "WASH/akses", "layanan persalinan", "outcome"]
TIER = {
    **dict.fromkeys(["perdesaan", "p0_daerah_mar2017", "pbi_pct_prov", "rasio_pkm_per_kec",
                     "pct_pkm_kurang_bidan", "sanitasi_klaster_lo", "cuci_tangan_klaster_lo",
                     "jarak_klaster_lo", "fasilitas_klaster_lo"], 0),
    **dict.fromkeys(["pend_ibu_thn", "umur_ibu", "urutan_lahir", "kembar", "anak_laki", "umur_anak_bln",
                     "jml_art", "kk_perempuan", "ibu_bekerja"], 1),
    **dict.fromkeys(["skor_kekayaan_nonwash", "org_per_kamar", "punya_ternak", "hambatan_biaya"], 2),
    **dict.fromkeys(["T_sanitasi", "air_layak", "olah_air_efektif", "cuci_tangan_dasar", "T_pbi",
                     "hambatan_jarak"], 3),
    **dict.fromkeys(["T_fasilitas", "M_anc4", "M_nakes", "M_sesar"], 4),
    **dict.fromkeys(["Y_diare", "Y_ispa", "Y_mati_neonatal", "Y_mati_bayi"], 5),
}
BASELINE = dict(
    boot=500,            # AUDIT: 100 -> 500, samakan dengan menu lain
    deff=2.16,           # AUDIT: nilai global untuk SEMUA analisis, padahal delta_bar per analisis 1,28-2,77.
                         # Perlu perubahan kode: hitung per analisis seperti N1.           # B1: design effect -> n efektif untuk chi2/RMSEA
    sem_exo_bebas=True,  # B1: kovarians antar-variabel eksogen diestimasi bebas (seperti lavaan)
    uji="campuran",      # B2: "campuran" = G2 bila semua variabel uji diskret, selain itu Fisher z; "fisher"
    alpha=0.05,          # AUDIT: 0,01 -> 0,05, samakan dengan SOL_V2 dan BENCH.alpha_uji
    maks_kondisi=3,      # B2: ukuran maksimum himpunan kondisi
    maks_kategori=5,     # B2/B3: variabel dengan <= sekian nilai unik dianggap diskret
    skor="gauss",        # AUDIT: "bic" -> "gauss". BIC diskret meledak pada node berinduk banyak:
                         # Y_diare di DAG pakar sanitasi punya 12 induk (7 biner + 5 kontinu x 4 bin)
                         # = 131.072 parameter, penalti ~635.000, cocok dengan skor pakar -673.067.
                         # Itu artefak skor, bukan bukti DAG pakar buruk.
    ess=1.0,             # B3: ukuran sampel ekuivalen alpha* untuk BDeu
    bin=4,               # B3: jumlah kuantil untuk memotong variabel kontinu
    maks_induk=5,        # B3: jumlah induk maksimum per node
    awal="kosong",       # B3: graf awal Hill-Climbing: "kosong" atau "pakar"
)

# ---------------------------------------------------------------------------
# NOVELTY (menu N1-N3, dokumen Tahap 3). Semua kandidat = hipotesis desain yang belum teruji.
# ---------------------------------------------------------------------------
NOVELTY = dict(
    boot=500,              # AUDIT: 100 -> 500
    # N1 SD-Hybrid
    sd_uji="desain",       # "desain" = Rao-Scott bila semua variabel uji diskret, selain itu t-desain; "t" = t-desain saja
    sd_alpha=0.05,         # AUDIT: ikut B2 (0,05) agar perbedaan tetap hanya dari koreksi desain
    sd_maks_kondisi=3,
    sd_skor="gauss",       # AUDIT: "bic" -> "gauss", alasan sama dengan BASELINE.skor
    sd_maks_induk=5,
    sd_rs_orde=2,          # koreksi Rao-Scott: 1 (bagi delta_bar) atau 2 (juga sesuaikan df dengan a^2)
    sd_skala="n_eff",      # skala likelihood skor s_w: "n_eff" (sama dengan penalti) atau "n" (rumusan awal)
    sim_rep=1000,          # AUDIT: 200 -> 1000; dengan 200, MC error galat tipe I ~ +-1,5 pp
    sim_icc=0.4,           # AUDIT: satu nilai saja. ICC diare IDHS ~0,15 (deff 2,17, ~9 kelahiran/klaster).
                           # Jalankan juga 0,05 dan 0,15 (grid v3 sudah heterogen).
    sim_efek=[0.0, 0.05, 0.10],   # korelasi laten X-Y: 0 = galat tipe I, > 0 = daya uji
                           # AUDIT: tidak ada parameter hubungan z dengan x dan y. Bila z dibangkitkan
                           # independen, uji S={z} = uji S=kosong (hasil identik di laporan). Periksa kode simulasi.
    # N2 TO-DAG
    to_skor="gauss",       # AUDIT: "bic" -> "gauss"
    to_berbobot=True,      # skor berbobot survei + penalti log n_eff (False = skor iid seperti B3)
    to_maks_induk=5,
    to_eksak_maks=8,       # tier dengan <= sekian variabel dicari eksak (DP subset); lebih besar -> pindah-posisi
    # N3 MLC-DAG
    mlc_penemuan="todag",  # penemuan struktur pada Sigma_V: "todag" (skor Gauss) atau "pc" (Fisher z)
    mlc_alpha=0.01,
    mlc_muatan_min=0.30,   # purifikasi: buang indikator dengan |lambda| lebih kecil
    mlc_tetrad_maks=0.05,  # purifikasi: rerata |tetrad| maksimum dalam konstruk
    mlc_lintas_maks=0.05,  # purifikasi: rerata |tetrad lintas konstruk| maksimum (indikator berhubungan langsung
                           # dengan dimensi lain)
)
MLC_KONSTRUK = {           # indikator (>= 3) per dimensi kemiskinan; treatment TIDAK dilebur ke konstruk
    "eta_ekonomi": ["ind_listrik", "ind_tv", "ind_kulkas", "ind_motor", "ind_mobil", "ind_bank",
                    "ind_lantai", "ind_dinding", "ind_atap"],
    "eta_pendidikan": ["pend_ibu_thn", "ind_pend_ibu_level", "pend_suami_kat"],
    "eta_kebersihan": ["cuci_tangan_dasar", "olah_air_efektif", "air_layak"],
    "eta_akses": ["hambatan_jarak", "hambatan_biaya", "rasio_pkm_per_kec", "pct_pkm_kurang_bidan"],
    # AUDIT: eta_akses mencampur indikator individu (hambatan_*) dengan indikator provinsi (rasio_pkm,
    # pct_pkm). Unit berbeda -> komposit tidak koheren. N3 tidak masuk naskah jurnal; perbaiki untuk disertasi.
}
MLC_JENIS = {              # N3 v2: "komposit" = indeks formatif (tanpa koreksi galat ukur);
    "eta_ekonomi": "komposit",        # "reflektif" = konstruk laten, dipertahankan hanya bila omega >= mlc_omega_min,
    "eta_pendidikan": "reflektif",    # bila tidak, indikatornya masuk graf sebagai node teramati terpisah
    "eta_kebersihan": "reflektif",
    "eta_akses": "komposit",
}
NOVELTY['mlc_omega_min'] = 0.70
MLC_TERAMATI = ["T_sanitasi", "T_pbi", "T_fasilitas", "umur_ibu", "urutan_lahir"]   # + outcome analisis
# AUDIT: ketiga treatment masuk ke SEMUA analisis -> SOL v2+MLC memilih T_pbi sebagai induk T_sanitasi dan
# T_sanitasi sebagai induk T_fasilitas, padahal tidak ada di DAG pakar dan sebagian diukur sesudahnya.
# Perlu perubahan kode: daftar teramati per analisis.
MLC_DIGANTI = {"skor_kekayaan_nonwash": "eta_ekonomi"}   # variabel DAG yang digantikan konstruk (tidak ikut sebagai node)
TIER.update(eta_pendidikan=1, eta_ekonomi=2, eta_kebersihan=3, eta_akses=3)

# ---------------------------------------------------------------------------
# SOL-DAG terintegrasi (MLC -> SD-Hybrid -> TO-DAG -> AIPW dengan pemisahan sampel per PSU)
# ---------------------------------------------------------------------------
# AUDIT: versi lama alpha SOL = 0,01 sedangkan SOL_V2 = 0,05 -> perbedaan v1 vs v2 tercampur dengan perbedaan alpha.
SOL = dict(boot=500, uji="desain", rs_orde=2, alpha=0.05, maks_kondisi=3, maks_induk=5, eksak_maks=8)
# AUDIT: jangan sebut "pra-registrasi" tanpa stempel waktu publik; tulis "rencana analisis terkunci (hash commit)".
SOL_V2 = dict(alpha=0.05, K=5)   # AUDIT: K 2 -> 5; cross-fitting 2 lipatan membuang separuh data untuk tiap model

# ---------------------------------------------------------------------------
# BENCHMARK semi-sintetik (graf benar diketahui, desain klaster IDHS dipertahankan)
# ---------------------------------------------------------------------------
BENCH = dict(
    rep=100,               # AUDIT v2: tetap 100. Benchmark v1 kini hanya pendukung; benchmark utama = BENCH_V4
    pekerja=3,             # proses paralel (core fisik dikurangi satu agar pengukuran waktu tidak terganggu)
    perturbasi=0.30,       # proporsi panah DAG pakar yang diganti untuk membentuk graf benar
                           # AUDIT: graf benar turunan DAG pakar menguntungkan B1. Jadikan benchmark v2/v3
                           # (DAG acak patuh tier) sebagai benchmark utama di naskah.
    boot=20,               # AUDIT v2: tetap 20 (200 membuat benchmark v1 ~10x lebih lama). Cakupan CI untuk naskah
                           # diambil dari BENCH_V4 yang memakai SE fungsi pengaruh + linearisasi desain, bukan bootstrap.
    n_populasi=20,         # AUDIT: 5 -> 20 agar galat Monte Carlo "efek benar" jauh di bawah RMSE yang dibandingkan
    alpha_uji=0.05,        # taraf untuk galat tipe I / daya uji pada pernyataan independensi yang benar
    n_pernyataan=20,       # jumlah pernyataan independensi dan dependensi benar yang diuji per replikasi
    skenario=["A", "B"],   # A = variabel teramati; B = konstruk laten (MLC)
)

# Variabel yang diringkas di EDA
EDA_VARS = ["T_pbi", "T_sanitasi", "T_fasilitas", "Y_diare", "Y_ispa", "Y_mati_neonatal",
            "Y_mati_bayi", "cuci_tangan_dasar", "air_layak", "olah_air_efektif", "hambatan_jarak",
            "hambatan_biaya", "pend_ibu_thn", "skor_kekayaan_nonwash", "perdesaan"]


# ---------------------------------------------------------------------------
# AUDIT v2 - BENCHMARK v4 (Fase 2): pemilihan confounder M0-M6, dibaca oleh bench_v4.py
# ---------------------------------------------------------------------------
BENCH_V4 = dict(
    rep=200,                        # replikasi per sel (~10-20 jam di laptop); pilot dulu: --rep 5
    icc=["heterogen", 0.15],        # heterogen = U(0,1; 0,8) per variabel; 0,15 ~ ICC diare IDHS
    beta_ty=[0.0, -0.15, -0.6],     # efek T -> Y pada skala laten probit
    kuat_confounder=["lemah", "kuat"],
    p=[15, 30],                     # jumlah node (termasuk T dan Y)
    alpha=0.05,                     # alpha uji untuk M2/M3
    alpha_T=[0.10, 0.20, 0.30],     # M4: alpha longgar (> alpha) untuk pasangan yang melibatkan T atau Y
    alpha_T_utama=0.10,             # M4 utama untuk H10-H13 (lainnya = sensitivitas)
    maks_kondisi=3,
    laten_frac=0.15,                # proporsi X yang tidak teramati oleh metode
    desain=(67, 29, 9),             # strata x PSU per strata x unit per PSU (setara IDHS 2017)
    K=5,                            # lipatan cross-fitting AIPW per PSU
    pekerja=3,
)
