# SOL v3 — S6–S10 (inti S8)
    pip install numpy pandas scipy statsmodels networkx
    python run_deff_real.py dataset.csv        # S6: deff tingkat-uji IDHS nyata (1 baris)
    python run_s8.py 200 [dataset.csv]          # S8 INTI: 5 uji CI, heterogen vs homogen -> RINGKASAN_S8.txt
    python run_downstream.py 100 15 [dataset.csv]  # S6+S7+S9: SHD, presisi, FDR, validitas penyesuaian, cakupan
Tempel hanya file RINGKASAN_*.txt saat berdiskusi. `dataset.csv` opsional: memakai bobot/PSU/strata IDHS asli.
Waktu (laptop): S8 ≈ 1 dtk/replikasi; hilir ≈ 9 dtk/replikasi (p=15, 5 uji).

| Fungsi (sol_v3.py) | Solusi |
|---|---|
| `t_naif`, `t_kish`, `t_deff_global`, `t_sandwich`, `t_desain` | S8: lima uji pembanding yang adil |
| `pair_deff`, `calibration` | S8: galat tipe I per bin deff; H0 dijamin via Markov lokal |
| `design_idhs`, `simulate_v3` | S6: desain IDHS asli/sintetis, ICC heterogen terkalibrasi |
| `valid_adjust`, `edge_metrics` | S7: validitas backdoor di graf acuan; presisi/recall/FDR |
| `effect_s9` | S9: cross-fitting berulang + interval gabungan kandidat IDA |
| `TEORI_S10.md` | S10: proposisi & sketsa bukti |
