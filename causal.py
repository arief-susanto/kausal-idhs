"""MENU 3: INFERENSI KAUSAL. DAG -> adjustment set (backdoor) -> g-komputasi, IPW, AIPW
+ bootstrap klaster (PSU dalam strata) + keseimbangan + E-value."""
import warnings
import numpy as np
import pandas as pd
import networkx as nx
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C
from eda import smd

warnings.filterwarnings("ignore")


def build_dag(spec):
    G = nx.DiGraph()
    for e in spec['edges']:
        a, b = [s.strip().format(T=spec['T'], Y=spec['Y']) for s in e.split('->')]
        G.add_edge(a, b)
    if not nx.is_directed_acyclic_graph(G):
        raise ValueError(f"DAG mengandung siklus: {nx.find_cycle(G)}")
    return G


def adjustment(G, T, Y, laten):
    """Himpunan ancestral: An(T,Y) \\ De(T) \\ laten, lalu diuji dg kriteria backdoor."""
    Z = (nx.ancestors(G, T) | nx.ancestors(G, Y)) - nx.descendants(G, T) - {T, Y} - set(laten)
    Gb = G.copy(); Gb.remove_edges_from(list(G.out_edges(T)))
    dsep = getattr(nx, "is_d_separator", None) or nx.d_separated   # networkx <3.3
    ok = dsep(Gb, {T}, {Y}, Z)
    mediator = sorted(nx.descendants(G, T) & nx.ancestors(G, Y))
    return sorted(Z), ok, mediator


def _fit(y, X, w):
    return sm.GLM(y, sm.add_constant(X, has_constant='add'), family=sm.families.Binomial(),
                  var_weights=w).fit(method='irls', maxiter=50)


def estimate(d, T, Y, Z):
    X = d[Z].astype(float); X = (X - X.mean()) / X.std(ddof=0).replace(0, 1)
    t, y, w = d[T].values, d[Y].values, d.bobot.values
    ps = _fit(t, X, w).predict(sm.add_constant(X, has_constant='add')).values
    ps = np.clip(ps, *np.quantile(ps, C.TRIM))
    om = _fit(y, X.assign(_T=t), w)
    X1, X0 = X.assign(_T=1), X.assign(_T=0)
    m1 = om.predict(sm.add_constant(X1, has_constant='add')).values
    m0 = om.predict(sm.add_constant(X0, has_constant='add')).values
    wa = lambda v: np.average(v, weights=w)
    r = {'gcomp_p1': wa(m1), 'gcomp_p0': wa(m0)}
    wi1, wi0 = w * t / ps, w * (1 - t) / (1 - ps)
    r['ipw_p1'], r['ipw_p0'] = (wi1 * y).sum() / wi1.sum(), (wi0 * y).sum() / wi0.sum()
    r['aipw_p1'] = wa(m1 + t * (y - m1) / ps); r['aipw_p0'] = wa(m0 + (1 - t) * (y - m0) / (1 - ps))
    for k in ('gcomp', 'ipw', 'aipw'):
        r[f'{k}_RD'] = r[f'{k}_p1'] - r[f'{k}_p0']; r[f'{k}_RR'] = r[f'{k}_p1'] / r[f'{k}_p0']
    return r, ps, wi1 + wi0


def bootstrap(d, T, Y, Z, B, rng, progress=None):
    """Resampling PSU dalam setiap strata (desain survei)."""
    psus = {s: g.psu.unique() for s, g in d.groupby('strata')}
    idx = {k: g.index.values for k, g in d.groupby(['strata', 'psu'])}
    res = []
    for i in range(B):
        take = np.concatenate([idx[(s, p)] for s, ps_ in psus.items() for p in rng.choice(ps_, len(ps_))])
        try:
            res.append(estimate(d.loc[take].reset_index(drop=True), T, Y, Z)[0])
        except Exception:
            pass
        if progress:
            progress(i + 1, B)
    return pd.DataFrame(res)


def evalue(rr):
    rr = 1 / rr if rr < 1 else rr
    return rr + np.sqrt(rr * (rr - 1))


def draw(G, spec, Z, out):
    col = {n: '#d62728' if n == spec['T'] else '#2ca02c' if n == spec['Y'] else '#bbbbbb'
           if n in spec['laten'] else '#1f77b4' if n in Z else '#ff7f0e' for n in G}
    for i, gen in enumerate(nx.topological_generations(G)):
        for v in gen:
            G.nodes[v]['lapis'] = i
    pos = nx.multipartite_layout(G, subset_key='lapis', align='horizontal', scale=2)
    pos = {k: (x, -y) for k, (x, y) in pos.items()}
    plt.figure(figsize=(14, 8))
    nx.draw_networkx(G, pos, node_color=[col[n] for n in G], node_size=600, font_size=7, connectionstyle='arc3,rad=0.08',
                     arrowsize=12, edge_color='#888888')
    plt.title("Merah=treatment, Hijau=outcome, Biru=dikontrol, Oranye=tidak dikontrol, Abu=laten")
    plt.axis('off'); plt.tight_layout(); plt.savefig(out / "dag.png", dpi=150); plt.close()


def cek_dag(nama=None):
    """Periksa DAG & identifikasi saja (tanpa data, tanpa estimasi) -> cepat."""
    lines = []
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = C.OUT / "kausal" / n; out.mkdir(parents=True, exist_ok=True)
        G = build_dag(spec); T, Y = spec['T'], spec['Y']
        Z, ok, med = adjustment(G, T, Y, spec['laten'])
        draw(G, spec, Z, out)
        lines += [f"DAG[{n}] {T}->{Y} identifikasi={'YA' if ok else 'TIDAK (ada laten)'} |Z|={len(Z)}",
                  f"DAG[{n}] dikontrol: {', '.join(Z)}",
                  f"DAG[{n}] mediator: {', '.join(med) or '-'} | laten: {', '.join(spec['laten']) or '-'}"]
    return lines


def run(df, nama=None, progress=None):
    rng = np.random.default_rng(C.SEED); lines = []
    for n, spec in C.ANALISIS.items():
        if nama and n != nama:
            continue
        out = C.OUT / "kausal" / n; out.mkdir(parents=True, exist_ok=True)
        G = build_dag(spec); T, Y = spec['T'], spec['Y']
        Z, ok, med = adjustment(G, T, Y, spec['laten'])
        miss = [z for z in Z if z not in df]
        if miss:
            raise KeyError(f"{n}: variabel tidak ada di dataset: {miss}")
        d = df.query(spec['filter']) if spec['filter'] else df
        d = d.dropna(subset=[T, Y] + Z).reset_index(drop=True)
        draw(G, spec, Z, out)
        est, ps, wipw = estimate(d, T, Y, Z)
        bs = bootstrap(d, T, Y, Z, C.BOOT, rng, progress and (lambda i, b, n=n: progress(n, i, b)))
        tab = pd.DataFrame({'estimasi': est, 'se_boot': bs.std(),
                            'ci_bawah': bs.quantile(.025), 'ci_atas': bs.quantile(.975)})
        tab.to_csv(out / "estimasi.csv")
        bal = pd.DataFrame({'smd_awal': {z: smd(d, T, z) for z in Z},
                            'smd_ipw': {z: smd(d.assign(bobot=wipw), T, z) for z in Z}})
        bal.to_csv(out / "keseimbangan.csv")
        plt.figure(figsize=(6, 3.5))
        for v, c in [(1, '#d62728'), (0, '#1f77b4')]:
            plt.hist(ps[d[T] == v], bins=40, alpha=.5, density=True, color=c, label=f'{T}={v}')
        plt.legend(); plt.xlabel('propensity score'); plt.tight_layout()
        plt.savefig(out / "overlap.png", dpi=150); plt.close()
        (out / "adjustment.txt").write_text(
            f"Teridentifikasi (backdoor): {ok}\nDikontrol ({len(Z)}): {', '.join(Z)}\n"
            f"Mediator (tidak dikontrol): {', '.join(med) or '-'}\nLaten: {', '.join(spec['laten']) or '-'}\n"
            f"Filter: {spec['filter'] or '-'}\nn analisis: {len(d)}\n")
        r = tab.loc
        rr_ci = r['aipw_RR', 'ci_bawah'] if est['aipw_RR'] > 1 else r['aipw_RR', 'ci_atas']
        ev_ci = 1.0 if (r['aipw_RR', 'ci_bawah'] <= 1 <= r['aipw_RR', 'ci_atas']) else evalue(rr_ci)
        lines += [f"KAUSAL[{n}] {T}->{Y} n={len(d)} |Z|={len(Z)} identifikasi={'YA' if ok else 'TIDAK (ada laten)'}"
                  f" mediator={','.join(med) or '-'}",
                  f"KAUSAL[{n}] AIPW RD={est['aipw_RD']:+.4f} [{r['aipw_RD', 'ci_bawah']:+.4f},{r['aipw_RD', 'ci_atas']:+.4f}]"
                  f" RR={est['aipw_RR']:.2f} [{r['aipw_RR', 'ci_bawah']:.2f},{r['aipw_RR', 'ci_atas']:.2f}]"
                  f" | gcomp RD={est['gcomp_RD']:+.4f} IPW RD={est['ipw_RD']:+.4f}",
                  f"KAUSAL[{n}] E-value titik={evalue(est['aipw_RR']):.2f} CI={ev_ci:.2f}"
                  f" | SMD maks setelah IPW={bal.smd_ipw.abs().max():.2f} | boot sah={len(bs)}/{C.BOOT}"]
    return lines
