# SOL-DAG v2 (solusi S1–S4) — hemat token

    pip install numpy pandas scipy statsmodels networkx
    python run_bench.py 200        # benchmark pra-registrasi v2 -> RINGKASAN_v2.txt (≤ 20 baris)
    python run_idhs.py dataset_analisis.csv sanitasi_diare pbi_diare

Tempel **hanya** `RINGKASAN_v2.txt` atau keluaran satu baris `run_idhs.py` saat berdiskusi.

| Fungsi (sol_v2.py) | Solusi | Isi |
|---|---|---|
| `ci_test` | S3 | Uji-t desain: kovarians residual berbobot, varians linearisasi PSU/strata, df = #PSU − #strata |
| `discover` | S3 | PC-stable + tier; sisi antar-tier diarahkan oleh tier, v-structure di dalam tier |
| `aipw_cf` | S2 | AIPW berbobot survei, nuisance di luar lipatan, SE fungsi pengaruh + linearisasi desain |
| `query_effect` | S1 | Himpunan penyesuaian = induk T (+ kombinasi tetangga tak berarah, ala IDA); efek selalu diestimasi |
| `simulate`, `benchmark` | S4 | DAG acak patuh tier, efek acak PSU (ICC), bobot, strata; metrik seragam + ablasi v1/naif |

Integrasi ke aplikasi Anda: ganti langkah estimasi SOL-DAG dengan `query_effect`, dan uji skeleton dengan `ci_test`.
MLC (konstruk) tetap dijalankan sebelumnya; masukkan skor/komposit konstruk sebagai kolom di `X`.
