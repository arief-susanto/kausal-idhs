"""MENU 2: EDA berbobot survei. Keluaran di hasil/eda/, ringkasan pendek ke layar."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C


def svy_mean(df, v):
    """Rata-rata berbobot + SE linearisasi Taylor (strata, PSU)."""
    x = df[[v, 'bobot', 'strata', 'psu']].dropna()
    W = x.bobot.sum(); m = np.average(x[v], weights=x.bobot)
    z = (x.bobot * (x[v] - m) / W).groupby([x.strata, x.psu]).sum().reset_index(name='z')
    var = sum(len(g) / (len(g) - 1) * ((g.z - g.z.mean()) ** 2).sum()
              for _, g in z.groupby('strata') if len(g) > 1)
    return m, np.sqrt(var), len(x)


def smd(df, t, v):
    """Standardized mean difference berbobot antara T=1 dan T=0."""
    x = df[[t, v, 'bobot']].dropna()
    a, b = x[x[t] == 1], x[x[t] == 0]
    if len(a) < 2 or len(b) < 2:
        return np.nan
    ma, mb = np.average(a[v], weights=a.bobot), np.average(b[v], weights=b.bobot)
    va = np.average((a[v] - ma) ** 2, weights=a.bobot); vb = np.average((b[v] - mb) ** 2, weights=b.bobot)
    return (ma - mb) / np.sqrt((va + vb) / 2) if va + vb > 0 else np.nan


def run(df):
    out = C.OUT / "eda"; out.mkdir(parents=True, exist_ok=True)
    num = df.select_dtypes('number').drop(columns=['bobot', 'psu', 'strata', 'klaster', 'rt', 'bidx'], errors='ignore')
    num = num[[c for c in num if not c.startswith('ind_')]]      # indikator MLC-DAG tidak diringkas di EDA

    miss = num.isna().mean().sort_values(ascending=False).rename('prop_kosong')
    miss.to_csv(out / "01_missing.csv")

    rows = []
    for v in C.EDA_VARS:
        m, se, n = svy_mean(df, v)
        rows.append(dict(variabel=v, rerata=m, se=se, ci_bawah=m - 1.96 * se, ci_atas=m + 1.96 * se, n=n))
    desk = pd.DataFrame(rows); desk.to_csv(out / "02_deskriptif_svy.csv", index=False)

    wm = lambda g, v: np.average(g[v].dropna(), weights=g.loc[g[v].notna(), 'bobot']) if g[v].notna().any() else np.nan
    ys = [c for c in df if c.startswith('Y_')]; ts = ['T_pbi', 'T_sanitasi', 'T_fasilitas']
    for by, f in [('kuintil_kekayaan_nonwash', '03_per_kuintil.csv'), ('provinsi', '04_per_provinsi.csv')]:
        df.groupby(by).apply(lambda g: pd.Series({v: wm(g, v) for v in ts + ys}),
                             include_groups=False).to_csv(out / f)

    cov = [c for c in num if not c.startswith(('T_', 'Y_', 'M_'))]
    bal = pd.DataFrame({t: {v: smd(df, t, v) for v in cov} for t in ts})
    bal.to_csv(out / "05_smd_per_treatment.csv")

    q = pd.read_csv(out / "03_per_kuintil.csv", index_col=0)
    ax = q[ts + ['Y_diare']].plot.bar(figsize=(8, 4), rot=0)
    ax.set_ylabel('proporsi berbobot'); ax.set_xlabel('kuintil kekayaan non-WASH')
    plt.tight_layout(); plt.savefig(out / "06_kuintil.png", dpi=150); plt.close()
    corr = num[[c for c in C.EDA_VARS if c in num]].corr()
    plt.figure(figsize=(7, 6)); plt.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1); plt.colorbar()
    plt.xticks(range(len(corr)), corr.columns, rotation=90, fontsize=7)
    plt.yticks(range(len(corr)), corr.columns, fontsize=7)
    plt.tight_layout(); plt.savefig(out / "07_korelasi.png", dpi=150); plt.close()

    lines = [f"EDA: kosong terbanyak {', '.join(f'{k}={v:.0%}' for k, v in miss.head(3).items())}"]
    for _, r in desk[desk.variabel.str.startswith(('T_', 'Y_'))].iterrows():
        lines.append(f"EDA: {r.variabel} {r.rerata:.3f} [{r.ci_bawah:.3f}-{r.ci_atas:.3f}] n={r.n}")
    for t in ts:
        top = bal[t].abs().sort_values(ascending=False)
        lines.append(f"EDA: {t} kovariat SMD>0.1={int((top > 0.1).sum())}; terbesar "
                     + ", ".join(f"{k}={bal[t][k]:+.2f}" for k in top.index[:3]))
    return lines
