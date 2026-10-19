"""Uji McNemar berpasangan validitas set penyesuaian M2 vs M3 (sel ICC heterogen).

Pakai:  python mcnemar_m2m3.py hasil/benchmark_v4/per_rep.csv
Analisis eksploratori (tidak termasuk H10-H13 yang dikunci). Hasilnya menggantikan
uji dua-proporsi konservatif (z = 4.0) di subbab 3.2 naskah.
"""
import sys
import pandas as pd
from scipy.stats import binomtest, chi2

jalur = sys.argv[1] if len(sys.argv) > 1 else "hasil/benchmark_v4/per_rep.csv"
d = pd.read_csv(jalur)
d = d[(d["icc"].astype(str) == "heterogen") & (d["metode"].isin(["M2", "M3"]))]
d["valid"] = d["valid"].astype(str).str.lower().isin(["true", "1"])
w = d.pivot_table(index=["sel", "rep"], columns="metode", values="valid", aggfunc="first").dropna()
w = w.astype(bool)

b = int((w["M2"] & ~w["M3"]).sum())   # valid hanya di M2
c = int((~w["M2"] & w["M3"]).sum())   # valid hanya di M3
n = len(w)
print(f"Pasangan replikasi: {n}")
print(f"Validitas M2 {w['M2'].mean():.3%}, M3 {w['M3'].mean():.3%}")
print(f"Diskordan: hanya M2 valid b={b}, hanya M3 valid c={c}")
p_eksak = binomtest(b, b + c, 0.5).pvalue if b + c else float("nan")
stat = (abs(b - c) - 1) ** 2 / (b + c) if b + c else float("nan")
print(f"McNemar eksak p = {p_eksak:.3g}; chi2 terkoreksi = {stat:.2f}, p = {chi2.sf(stat, 1):.3g}")
print("Kalimat naskah: (paired McNemar test, b = %d, c = %d, p %s)"
      % (b, c, "< 0.001" if p_eksak < 0.001 else f"= {p_eksak:.3f}"))
