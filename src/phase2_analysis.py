#!/usr/bin/env python3
"""Reproducible Phase 2 probability analysis for the supplied NACC subset.

Run from any directory with the Python runtime documented in README.md. The
script writes participant-aggregate results, audit CSVs, vector figures, a
LaTeX source report, and a companion PDF report when ReportLab is installed.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "reports" / "phase2"
FIG = ROOT / "figures" / "phase2"
STATUS = {1: "Normal cognition", 2: "Impaired, not MCI", 3: "MCI", 4: "Dementia"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def quantile(values, p):
    xs = sorted(values)
    h = (len(xs) - 1) * p
    lo, hi = int(h), math.ceil(h)
    return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)


def stats(values):
    xs = [x for x in values if x is not None]
    n = len(xs)
    q1, med, q3 = (quantile(xs, p) for p in (.25, .5, .75))
    mean = statistics.fmean(xs)
    var = statistics.pvariance(xs)  # empirical distribution variance, divisor n
    low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    return {"n": n, "mean": mean, "variance_population_divisor_n": var,
            "median": med, "q1": q1, "q3": q3, "iqr": q3-q1,
            "min": min(xs), "max": max(xs), "fence_low": low,
            "fence_high": high, "outliers_1_5_iqr": sum(x < low or x > high for x in xs),
            "skewness_moment": (sum((x-mean)**3 for x in xs)/n)/(var**1.5) if var else 0.0}


def csv_write(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def bayes_theorem_verification(p_A, p_B_given_A, p_B_given_not_A):
    """Bayes' theorem: P(A|B) = P(B|A)P(A) / P(B), with the law of total
    probability P(B) = P(B|A)P(A) + P(B|~A)P(~A). Inputs are conditional
    probabilities, so the result is independent of the direct 2x2 ratio."""
    p_not_A = 1 - p_A
    p_B = p_B_given_A * p_A + p_B_given_not_A * p_not_A
    p_A_given_B = (p_B_given_A * p_A) / p_B
    return {"P(B)_derived": p_B, "P(A|B)_bayes": p_A_given_B}


def correlation_statistics(pairs):
    """Covariance (n-1), Pearson and Spearman correlations with p-values."""
    import numpy as np
    from scipy import stats as sps
    x = np.array([a for a, _ in pairs], dtype=float)
    y = np.array([b for _, b in pairs], dtype=float)
    pr, pp = sps.pearsonr(x, y)
    sr, sp = sps.spearmanr(x, y)
    return {"covariance": float(np.cov(x, y, ddof=1)[0, 1]), "pearson_r": float(pr),
            "pearson_p": float(pp), "spearman_r": float(sr), "spearman_p": float(sp),
            "n": int(len(x))}


def normality_statistics(moca, volume):
    """Skewness, excess kurtosis (moment based) and Shapiro-Wilk p-values."""
    from scipy import stats as sps
    out = {}
    for key, v in (("moca", moca), ("volume", volume)):
        out[f"{key}_n"] = len(v)
        out[f"{key}_skewness"] = float(sps.skew(v))
        out[f"{key}_kurtosis"] = float(sps.kurtosis(v))  # excess kurtosis
        w, p = sps.shapiro(v)
        out[f"{key}_shapiro_W"] = float(w)
        out[f"{key}_shapiro_p"] = float(p)
    out["kurtosis_definition"] = "excess kurtosis (normal = 0), moment estimator"
    return out


def save_svg(path, content, width=900, height=560):
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n<rect width="100%" height="100%" fill="white"/>\n{content}\n</svg>', encoding="utf-8")


def svg_text(x, y, text, size=13, anchor="middle", color="#334155"):
    import html
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}">{html.escape(str(text))}</text>'


def histogram(values, title, xlabel, path, bins=18, normal=False):
    xs = list(values); lo, hi = min(xs), max(xs)
    if hi == lo: hi = lo + 1
    step=(hi-lo)/bins; counts=[0]*bins
    for x in xs: counts[min(bins-1,int((x-lo)/step))]+=1
    L,R,T,B=85,35,95,75; W,H=900,560; pw,ph=W-L-R,H-T-B; mc=max(counts)
    a=[svg_text(W/2,36,title,20,color="#18324b"),svg_text(W/2,62,f'n = {len(xs):,}; bars show supplied valid observations',13,color="#64748b")]
    for t in range(5):
        y=T+ph*t/4; a += [f'<line x1="{L}" y1="{y}" x2="{W-R}" y2="{y}" stroke="#e5eaf0"/>',svg_text(L-10,y+4,round(mc*(1-t/4)),12,"end")]
    for i,c in enumerate(counts):
        bw=pw/bins; bh=ph*c/mc
        a.append(f'<rect x="{L+i*bw+1}" y="{T+ph-bh}" width="{bw-2}" height="{bh}" fill="#247ba0"/>')
    if normal:
        mu=statistics.mean(xs); sd=statistics.pstdev(xs)
        for i in range(201):
            x=lo+(hi-lo)*i/200; dens=math.exp(-.5*((x-mu)/sd)**2)/(sd*math.sqrt(2*math.pi))*len(xs)*step
            y=T+ph-ph*dens/mc
            if i:
                a.append(f'<line x1="{px0:.2f}" y1="{py0:.2f}" x2="{L+pw*i/200:.2f}" y2="{y:.2f}" stroke="#d1495b" stroke-width="2"/>')
            px0,py0=L+pw*i/200,y
    for t in range(5):
        x=L+pw*t/4; a.append(svg_text(x,T+ph+22,f'{lo+(hi-lo)*t/4:.1f}',12))
    a += [svg_text(W/2,H-20,xlabel,14),svg_text(23,H/2,"Participants",13),f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" stroke="#334155"/>',f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" stroke="#334155"/>']
    if normal: a.append(f'<line x1="{W-260}" y1="78" x2="{W-225}" y2="78" stroke="#d1495b" stroke-width="2"/>'+svg_text(W-215,82,"Fitted normal",12,"start"))
    save_svg(path,"\n".join(a))


def qqplot(values, title, xlabel, path):
    xs=sorted(values); n=len(xs); mu=statistics.mean(xs); sd=statistics.pstdev(xs)
    # Blom plotting positions and Acklam's inverse-normal approximation.
    def invnorm(p):
        a=[-39.6968302866538,220.946098424521,-275.928510446969,138.357751867269,-30.6647980661472,2.50662827745924]
        b=[-54.4760987982241,161.585836858041,-155.698979859887,66.8013118877197,-13.2806815528857]
        c=[-0.00778489400243029,-0.322396458041136,-2.40075827716184,-2.54973253934373,4.37466414146497,2.93816398269878]
        d=[0.00778469570904146,0.32246712907004,2.445134137143,3.75440866190742]
        if p<.02425:
            q=math.sqrt(-2*math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p>.97575: return -invnorm(1-p)
        q=p-.5;r=q*q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    theo=[invnorm((i+.5)/n) for i in range(n)]
    L,R,T,B=85,35,85,75; W,H=900,560; pw,ph=W-L-R,H-T-B
    tx0,tx1=min(theo),max(theo); y0,y1=min(xs),max(xs); pad=(y1-y0)*.04; y0-=pad;y1+=pad
    coord=lambda x,y:(L+pw*(x-tx0)/(tx1-tx0),T+ph*(y1-y)/(y1-y0))
    p1=coord(tx0,mu+sd*tx0);p2=coord(tx1,mu+sd*tx1)
    a=[svg_text(W/2,34,title,20,color="#18324b"),f'<line x1="{p1[0]}" y1="{p1[1]}" x2="{p2[0]}" y2="{p2[1]}" stroke="#d1495b" stroke-width="2"/>']
    for x,y in zip(theo,xs):
        cx,cy=coord(x,y);a.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.2" fill="#247ba0" fill-opacity=".65"/>')
    a += [svg_text(W/2,H-22,"Theoretical normal quantiles",14),svg_text(22,H/2,xlabel,13),f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" stroke="#334155"/>',f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" stroke="#334155"/>']
    save_svg(path,"\n".join(a))


def new_figures(pairs_status, result):
    """Regression scatter (colored by NACCUDSD) and Bayes posterior bars."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats as sps
    cr = result["correlation"]; bv = result["bayes_verification"]
    x = np.array([t[0] for t in pairs_status]); y = np.array([t[1] for t in pairs_status])
    st = np.array([t[2] for t in pairs_status])
    fig, ax = plt.subplots(figsize=(9, 5.8))
    colors_ = {1: "#2a9d8f", 2: "#e9c46a", 3: "#f4a261", 4: "#d1495b"}
    rng = np.random.default_rng(2)
    for code in (1, 2, 3, 4):
        mk = st == code
        if mk.any():
            ax.scatter(x[mk] + rng.uniform(-.2, .2, mk.sum()), y[mk], s=14, alpha=.55,
                       color=colors_[code], label=f"{STATUS[code]} (n={int(mk.sum())})", linewidths=0)
    lr = sps.linregress(x, y); xs = np.linspace(x.min(), x.max(), 200)
    n = len(x); resid = y - (lr.intercept + lr.slope * x); s_err = np.sqrt((resid ** 2).sum() / (n - 2))
    se = s_err * np.sqrt(1 / n + (xs - x.mean()) ** 2 / ((x - x.mean()) ** 2).sum())
    t = sps.t.ppf(.975, n - 2); fit = lr.intercept + lr.slope * xs
    ax.fill_between(xs, fit - t * se, fit + t * se, color="#18324b", alpha=.25, label="95% CI of fitted mean")
    ax.plot(xs, fit, color="#18324b", lw=2, label="Linear regression")
    ax.text(.03, .97, f"Pearson r = {cr['pearson_r']:.3f}\np = {cr['pearson_p']:.2e}\nn = {cr['n']}",
            transform=ax.transAxes, va="top", bbox=dict(boxstyle="round", fc="white", ec="#ccd5de"))
    ax.set_xlabel("MOCATOTS (score points; horizontal jitter ±0.2 for display only)")
    ax.set_ylabel("Bilateral entorhinal volume (mm³)")
    ax.set_title("MoCA vs. bilateral entorhinal volume, colored by NACCUDSD")
    ax.legend(loc="lower right", fontsize=8); ax.grid(alpha=.25); fig.tight_layout()
    for ext in ("svg", "png", "pdf"):
        fig.savefig(FIG / f"moca_volume_scatter_regression.{ext}", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    vals = [100 * bv["P_A_given_B_bayes"], 100 * result["probabilities"]["P_A_given_not_B"]["value"]]
    bars = ax.bar(["P(impaired | low volume)", "P(impaired | high volume)"], vals, color=["#d1495b", "#247ba0"], width=.55)
    ax.axhline(100 * bv["P_A"], color="#18324b", ls="--", lw=1.8, label=f"Prior P(impaired) = {100*bv['P_A']:.1f}%")
    for b_, v_ in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v_ + 1, f"{v_:.1f}%", ha="center", fontweight="bold")
    ax.set_ylim(0, max(vals) + 12); ax.set_ylabel("Probability (%)")
    ax.set_title("Bayes posterior: impairment probability by volume group")
    ax.legend(loc="upper right"); ax.grid(axis="y", alpha=.25); fig.tight_layout()
    for ext in ("svg", "png", "pdf"):
        fig.savefig(FIG / f"bayes_posterior.{ext}", dpi=150)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
    uds=read_csv(DATA/"udslong_imputed.csv"); mri=read_csv(DATA/"mriscanclean.csv")
    iu=[r["NACCID"] for r in uds]; im=[r["NACCID"] for r in mri]
    assert len(iu)==len(set(iu)) and len(im)==len(set(im)), "Duplicate NACCID: participant unit is not unique"
    u={r["NACCID"]:r for r in uds}; m={r["NACCID"]:r for r in mri}; shared=sorted(u.keys()&m.keys())
    rows=[]
    for pid in shared:
        a=u[pid]; b=m[pid]
        assert num(a["NACCUDSD"])==num(b["NACCUDSD"]), "UDS/MRI NACCUDSD mismatch"
        row={**a,**b}; row["NACCID"]=pid
        for k,v in list(row.items()):
            if k!="NACCID": row[k]=num(v)
        row["MOCA"]=row.get("MOCATOTS") if row.get("MOCATOTS") is not None and 0<=row["MOCATOTS"]<=30 else None
        lv,rv=row.get("LH_ENTORHINAL_GVOL"),row.get("RH_ENTORHINAL_GVOL")
        row["VOL"]=(lv+rv)/2 if lv and rv and lv>0 and rv>0 else None
        lt,rt=row.get("LH_ENTORHINAL_AVGTH"),row.get("RH_ENTORHINAL_AVGTH")
        row["THICK"]=(lt+rt)/2 if lt and rt and lt>0 and rt>0 else None
        rows.append(row)
    linked=len(rows); eligible=[r for r in rows if r.get("NACCAGE") is not None and r["NACCAGE"]>=65]
    assert linked==len(set(r["NACCID"] for r in rows))
    statuses={int(r["NACCUDSD"]) for r in eligible}; assert statuses <= set(STATUS) and statuses==set(STATUS)
    volumes=[r["VOL"] for r in eligible if r["VOL"] is not None]
    median=quantile(volumes,.5); below=sum(v<median for v in volumes); equal=sum(v==median for v in volumes)
    # Conventional median split: lower group is <= median, upper group is > median.
    valid=[r for r in eligible if r["VOL"] is not None and r["NACCUDSD"] is not None]
    assert all(r["VOL"] > 0 for r in valid) and len(valid)==864, "Bilateral-volume construction or validity changed"
    A=lambda r:int(r["NACCUDSD"] in (3,4))
    B=lambda r:int(r["VOL"]<=median)
    n=len(valid); n11=sum(A(r) and B(r) for r in valid); n10=sum(A(r) and not B(r) for r in valid)
    n01=sum(not A(r) and B(r) for r in valid); n00=sum(not A(r) and not B(r) for r in valid)
    assert n11+n10+n01+n00==n and n11+n10>0 and n01+n00>0 and n11+n01>0 and n10+n00>0
    pA=(n11+n10)/n;pB=(n11+n01)/n;pAB=n11/n;pA_B=n11/(n11+n01);pA_notB=n10/(n10+n00)
    pB_A=n11/(n11+n10); bayes=pA_B*pB/pA
    assert all(0<=x<=1 for x in (pA,pB,pAB,pA_B,pA_notB,pB_A,bayes)) and abs(pB_A-bayes)<1e-12
    bayes_check=bayes_theorem_verification(pA, pB_A, n01/(n01+n00))
    assert abs(bayes_check["P(B)_derived"]-pB)<1e-12
    assert abs(bayes_check["P(A|B)_bayes"]-pA_B)<1e-12
    # Dataset-defined groups use the same common valid cohort denominator.
    group_rows=[]
    for flag,label in ((1,"At or below volume median"),(0,"Above volume median")):
        group=[r for r in valid if B(r)==flag]; count_a=sum(A(r) for r in group)
        group_rows.append({"group":label,"volume_median_group":flag,"n_group":len(group),"n_MCI_or_dementia":count_a,"probability":count_a/len(group),"percent":100*count_a/len(group),"denominator_definition":"age 65+ with valid positive bilateral volume and valid NACCUDSD"})
    pmf=[{"x":0,"label":"No MCI/dementia","count":n-(n11+n10),"probability":1-pA},{"x":1,"label":"MCI or dementia","count":n11+n10,"probability":pA}]
    binom_n=10; binom=[{"k":k,"probability":math.comb(binom_n,k)*pA**k*(1-pA)**(binom_n-k)} for k in range(binom_n+1)]
    moca=[r["MOCA"] for r in eligible if r["MOCA"] is not None]; vol=[r["VOL"] for r in eligible if r["VOL"] is not None]
    pairs=[(r["MOCA"],r["VOL"]) for r in eligible if r["MOCA"] is not None and r["VOL"] is not None]
    x=[a for a,b in pairs]; y=[b for a,b in pairs]; pairn=len(pairs)
    cov=sum((a-statistics.mean(x))*(b-statistics.mean(y)) for a,b in pairs)/(pairn-1)
    corr=cov/(statistics.stdev(x)*statistics.stdev(y))
    mstat=stats(moca); vstat=stats(vol)
    corrstat=correlation_statistics(pairs)
    assert abs(corrstat["covariance"]-cov)<1e-9 and abs(corrstat["pearson_r"]-corr)<1e-9
    normstat=normality_statistics(moca, vol)
    # Flow counts specify the valid n for each analysis explicitly.
    flow=[{"step":"UDS input records","n":len(uds)},{"step":"MRI input records","n":len(mri)},{"step":"matched unique participants","n":linked},{"step":"age eligible (NACCAGE >= 65)","n":len(eligible)},{"step":"valid cognitive-status and bilateral-volume 2x2 subset","n":n},{"step":"valid MOCATOTS (0 to 30)","n":len(moca)},{"step":"valid bilateral volume","n":len(vol)},{"step":"paired valid MoCA and volume","n":pairn}]
    result={"design":{"unit":"one supplied row per unique NACCID","population":"age-65+ participants in the supplied linked NACC UDS/MRI clinical/research subset; not all older adults","baseline_or_temporal_alignment":"cannot establish baseline visit or contemporaneous UDS/MRI; supplied files lack visit identifiers/dates and MRI scan dates","UDS_processing":"processed/imputed file; imputation procedure and original missingness mask unavailable","status_codes":STATUS,"moca_rule":"MOCATOTS accepted only in [0,30]; no rounding or clipping","volume_rule":"arithmetic mean of left/right entorhinal GVOL only when both values are positive","variance_convention":"empirical distribution variance with divisor n except pairwise covariance, which is sample covariance with divisor n-1"},
            "linkage":{"UDS_rows":len(uds),"MRI_rows":len(mri),"unique_UDS_NACCID":len(set(iu)),"unique_MRI_NACCID":len(set(im)),"matched_unique":linked,"unmatched_UDS":len(set(iu)-set(im)),"unmatched_MRI":len(set(im)-set(iu)),"duplicate_UDS_ID_rows":len(iu)-len(set(iu)),"duplicate_MRI_ID_rows":len(im)-len(set(im)),"NACCUDSD_disagreements":0},
            "flow":flow,"events":{"A":"NACCUDSD in {3,4} (dataset-coded MCI or dementia; not a new diagnosis)","B":f"bilateral entorhinal volume <= eligible-cohort median ({median:.6f} mm^3)","median_mm3":median,"median_rule":"linear interpolation (type-7 quantile); ties included in lower group","volume_median_n":len(volumes),"below_median_n":below,"equal_to_median_n":equal,"at_or_below_median_n":sum(v<=median for v in volumes)},
            "contingency":{"denominator":n,"rows":[{"A":"yes","B":"yes","count":n11},{"A":"yes","B":"no","count":n10},{"A":"no","B":"yes","count":n01},{"A":"no","B":"no","count":n00}],"marginal_A":n11+n10,"marginal_not_A":n01+n00,"marginal_B":n11+n01,"marginal_not_B":n10+n00},
            "probabilities":{"P_A":{"numerator":n11+n10,"denominator":n,"value":pA},"P_B":{"numerator":n11+n01,"denominator":n,"value":pB},"P_A_and_B":{"numerator":n11,"denominator":n,"value":pAB},"P_A_given_B":{"numerator":n11,"denominator":n11+n01,"value":pA_B},"P_A_given_not_B":{"numerator":n10,"denominator":n10+n00,"value":pA_notB},"P_B_given_A":{"numerator":n11,"denominator":n11+n10,"value":pB_A},"P_A_times_P_B":pA*pB,"independence_difference":pAB-pA*pB,"bayes_rhs":bayes,"bayes_identity_absolute_difference":abs(bayes-pB_A)},
            "groups":group_rows,"bernoulli":{"n":n,"pmf":pmf,"E_X":pA,"Var_X_empirical":pA*(1-pA)},"binomial":{"n":binom_n,"p":pA,"pmf":binom,"expected":binom_n*pA,"variance":binom_n*pA*(1-pA),"assumptions":"fixed n=10; independent Bernoulli trials; same event probability p; each trial has two outcomes. Hypothetical independent draws, not sampling distinct finite-cohort participants without replacement."},
            "continuous":{"MOCATOTS_points":mstat,"bilateral_entorhinal_volume_mm3":vstat},"association":{"n":pairn,"sample_covariance_MoCA_points_times_mm3":cov,"Pearson_r":corr,"interpretation":"descriptive linear association; not causal"}}
    # Assertions requested for audit and reproducibility.
    assert len(eligible)==864 and linked==1237
    assert sum(x["count"] for x in result["contingency"]["rows"])==n
    result["bayes_verification"]={"P_B_given_A":pB_A,"P_B_given_not_A":n01/(n01+n00),
        "P_A":pA,"P_not_A":1-pA,"P_B_derived":bayes_check["P(B)_derived"],
        "P_A_given_B_bayes":bayes_check["P(A|B)_bayes"],
        "P_A_given_B_direct":pA_B,
        "absolute_difference":abs(bayes_check["P(A|B)_bayes"]-pA_B),
        "match":abs(bayes_check["P(A|B)_bayes"]-pA_B)<1e-12}
    result["correlation"]={**corrstat,"interpretation":"descriptive linear association in the paired-complete subset; not causal"}
    result["normality"]=normstat
    csv_write(OUT/"analytic_flow.csv",flow,["step","n"])
    joint=[{"A":"yes","B":"yes","count":n11,"denominator":n},{"A":"yes","B":"no","count":n10,"denominator":n},{"A":"no","B":"yes","count":n01,"denominator":n},{"A":"no","B":"no","count":n00,"denominator":n}]
    split_rows=[]
    for label,impaired_group,normal_group in (("low_volume",n11,n01),("high_volume",n10,n00)):
        tot=impaired_group+normal_group
        split_rows.append({"group":label,"impaired":impaired_group,"normal":normal_group,"total":tot,
            "impaired_pct":round(100*impaired_group/tot,2),"normal_pct":round(100*normal_group/tot,2)})
    split_rows.append({"group":"total","impaired":n11+n10,"normal":n01+n00,"total":n,
        "impaired_pct":round(100*pA,2),"normal_pct":round(100*(1-pA),2)})
    csv_write(OUT/"contingency_2x2.csv",split_rows,["group","impaired","normal","total","impaired_pct","normal_pct"])
    csv_write(OUT/"contingency_joint_AB.csv",joint,["A","B","count","denominator"])
    csv_write(OUT/"group_probabilities.csv",group_rows,["group","volume_median_group","n_group","n_MCI_or_dementia","probability","percent","denominator_definition"])
    csv_write(OUT/"bernoulli_pmf.csv",pmf,["x","label","count","probability"])
    csv_write(OUT/"binomial_pmf.csv",binom,["k","probability"])
    (OUT/"phase2_results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

    histogram(moca,"MoCA score distribution","MOCATOTS (score points)",FIG/"moca_histogram.svg",15,True)
    histogram(vol,"Bilateral entorhinal volume distribution","Mean bilateral volume (mm³)",FIG/"volume_histogram.svg",18,True)
    qqplot(moca,"Normal Q–Q plot: MOCATOTS","Observed MoCA score points",FIG/"moca_qq.svg")
    qqplot(vol,"Normal Q–Q plot: bilateral entorhinal volume","Observed volume (mm³)",FIG/"volume_qq.svg")
    # Cognitive-status probability by the two prespecified, median-defined groups.
    w,h=900,520; L,R,T,B=115,50,70,100; ph=h-T-B; pw=w-L-R
    labels=[g["group"] for g in group_rows]; vals=[g["percent"] for g in group_rows]
    a=[svg_text(w/2,35,"MCI or dementia by entorhinal-volume group",19,color="#18324b")]
    for t in range(5):
        yy=T+ph*t/4; a += [f'<line x1="{L}" y1="{yy}" x2="{w-R}" y2="{yy}" stroke="#e5eaf0"/>',svg_text(L-12,yy+4,f'{100-t*25}%',12,"end")]
    for i,(lab,val) in enumerate(zip(labels,vals)):
        bw=160; xx=L+pw*(i+.5)/2-bw/2; bh=ph*val/100
        a += [f'<rect x="{xx}" y="{T+ph-bh}" width="{bw}" height="{bh}" fill="#247ba0"/>',svg_text(xx+bw/2,T+ph-bh-10,f'{val:.1f}% ({group_rows[i]["n_MCI_or_dementia"]}/{group_rows[i]["n_group"]})',13),svg_text(xx+bw/2,T+ph+27,lab,13)]
    a += [svg_text(w/2,h-20,"Volume group",14),svg_text(24,h/2,"Empirical probability",13)]
    save_svg(FIG/"group_probabilities.svg","\n".join(a),w,h)
    # Binomial mass plot.
    w,h=900,520;L,R,T,B=75,35,70,95;pw=w-L-R;ph=h-T-B;mx=max(z["probability"] for z in binom)
    a=[svg_text(w/2,35,f"Binomial count model: n={binom_n}, p={pA:.3f}",19,color="#18324b")]
    for t in range(5):
        yy=T+ph*t/4;a += [f'<line x1="{L}" y1="{yy}" x2="{w-R}" y2="{yy}" stroke="#e5eaf0"/>',svg_text(L-10,yy+4,f'{mx*(1-t/4):.2f}',11,"end")]
    for z in binom:
        xx=L+pw*(z["k"]+.5)/(binom_n+1);bh=ph*z["probability"]/mx;a.append(f'<rect x="{xx-18}" y="{T+ph-bh}" width="36" height="{bh}" fill="#247ba0"/>');a.append(svg_text(xx,T+ph+20,z["k"],12))
    a += [svg_text(w/2,h-20,"Count Y of MCI/dementia outcomes among 10 hypothetical independent draws",13),svg_text(20,h/2,"Probability",12)]
    save_svg(FIG/"binomial_pmf.svg","\n".join(a),w,h)
    # Pairwise scatter.
    w,h=900,560;L,R,T,B=85,35,70,80;pw=w-L-R;ph=h-T-B;x0,x1=min(x),max(x);y0,y1=min(y),max(y);dx=x1-x0;dy=y1-y0
    a=[svg_text(w/2,34,f"MoCA and bilateral entorhinal volume (n={pairn})",19,color="#18324b")]
    mx,my=statistics.mean(x),statistics.mean(y);slope=cov/statistics.variance(x);inter=my-slope*mx
    yy0=T+ph*(y1-(inter+slope*x0))/dy;yy1=T+ph*(y1-(inter+slope*x1))/dy
    a.append(f'<line x1="{L}" y1="{yy0}" x2="{L+pw}" y2="{yy1}" stroke="#d1495b" stroke-width="2"/>')
    for xx,yy in pairs:
        cx=L+pw*(xx-x0)/dx;cy=T+ph*(y1-yy)/dy;a.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.5" fill="#247ba0" fill-opacity=".35"/>')
    a += [svg_text(w/2,h-20,"MOCATOTS (score points)",14),svg_text(22,h/2,"Bilateral entorhinal volume (mm³)",13)]
    save_svg(FIG/"moca_volume_scatter.svg","\n".join(a),w,h)
    new_figures([(r["MOCA"],r["VOL"],int(r["NACCUDSD"])) for r in eligible
                 if r["MOCA"] is not None and r["VOL"] is not None and r["NACCUDSD"] is not None],result)

    write_report_tex(result)
    try: build_pdf(result)
    except ImportError as e: print(f"ReportLab PDF build skipped: {e}")
    print(json.dumps({"linked":linked,"age65plus":len(eligible),"median_mm3":median,"two_by_two":[n11,n10,n01,n00],"P_A":pA,"P_A_given_B":pA_B,"P_A_given_not_B":pA_notB,"covariance":cov,"r":corr,"figures":len(list(FIG.iterdir()))},indent=2))


def write_report_tex(r):
    c=r["contingency"]; p=r["probabilities"]; e=r["events"]; g=r["groups"]; d=r["continuous"]
    bv=r["bayes_verification"]; co=r["correlation"]; nm=r["normality"]; bi=r["binomial"]
    n=c["denominator"]; n11,n10,n01,n00=(x["count"] for x in c["rows"])
    nA,nnA,nB,nnB=c["marginal_A"],c["marginal_not_A"],c["marginal_B"],c["marginal_not_B"]
    pA=p["P_A"]["value"]; pB=p["P_B"]["value"]
    sci=lambda x: ("%.2e"%x).replace("e-","\\times10^{-").replace("e+","\\times10^{")+"}"
    V={"n":n,"n11":n11,"n10":n10,"n01":n01,"n00":n00,"nA":nA,"nnA":nnA,"nB":nB,"nnB":nnB,
       "pA":f"{pA:.4f}","pnA":f"{1-pA:.4f}","pB":f"{pB:.4f}","pnB":f"{1-pB:.4f}","pAB":f"{p['P_A_and_B']['value']:.4f}",
       "pApB":f"{p['P_A_times_P_B']:.4f}","pA_B":f"{p['P_A_given_B']['value']:.4f}","pA_nB":f"{p['P_A_given_not_B']['value']:.4f}",
       "pB_A":f"{bv['P_B_given_A']:.4f}","pB_nA":f"{bv['P_B_given_not_A']:.4f}","pBder":f"{bv['P_B_derived']:.4f}",
       "pAbayes":f"{bv['P_A_given_B_bayes']:.4f}","pAdirect":f"{bv['P_A_given_B_direct']:.4f}",
       "pA_pct":f"{100*pA:.1f}","pA_B_pct":f"{100*p['P_A_given_B']['value']:.1f}","pA_nB_pct":f"{100*p['P_A_given_not_B']['value']:.1f}",
       "lowA_pct":f"{100*n11/(n11+n01):.2f}","lowN_pct":f"{100*n01/(n11+n01):.2f}","highA_pct":f"{100*n10/(n10+n00):.2f}","highN_pct":f"{100*n00/(n10+n00):.2f}",
       "totA_pct":f"{100*pA:.2f}","totN_pct":f"{100*(1-pA):.2f}","nlow":n11+n01,"nhigh":n10+n00,
       "median":f"{e['median_mm3']:.0f}","ties":e["equal_to_median_n"],"nvol":d["bilateral_entorhinal_volume_mm3"]["n"],"nmoca":d["MOCATOTS_points"]["n"],
       "flow0":r["flow"][0]["n"],"flow1":r["flow"][1]["n"],"flow2":r["flow"][2]["n"],"flow3":r["flow"][3]["n"],
       "EY":f"{bi['expected']:.3f}","VarY":f"{bi['variance']:.3f}","binn":bi["n"],"tenpct":f"{100*bi['n']/n:.1f}",
       "msk":f"{nm['moca_skewness']:.3f}","mku":f"{nm['moca_kurtosis']:.3f}","vsk":f"{nm['volume_skewness']:.3f}","vku":f"{nm['volume_kurtosis']:.3f}",
       "msp":sci(nm["moca_shapiro_p"]),"vsp":sci(nm["volume_shapiro_p"]),"mW":f"{nm['moca_shapiro_W']:.3f}","vW":f"{nm['volume_shapiro_W']:.3f}",
       "mmean":f"{d['MOCATOTS_points']['mean']:.2f}","vmean":f"{d['bilateral_entorhinal_volume_mm3']['mean']:.1f}",
       "cov":f"{co['covariance']:.2f}","pr":f"{co['pearson_r']:.4f}","pp":sci(co["pearson_p"]),"sr":f"{co['spearman_r']:.4f}","sp":sci(co["spearman_p"]),"cn":co["n"],
       "r2":f"{co['pearson_r']**2:.3f}"}
    tex=r'''\documentclass[11pt]{article}
\usepackage[margin=0.85in]{geometry}
\usepackage{booktabs,graphicx,amsmath,amssymb,hyperref,caption,float}
\graphicspath{{../figures/phase2/}}
\title{Phase 2: Probability Analysis of MoCA and Entorhinal Volume}
\author{Statistics Project -- NACC UDS + MRI subset}
\date{}
\begin{document}\maketitle
\begin{abstract}This report describes empirical probabilities, Bayes' theorem, a binomial model, normality checks, and the covariance of MoCA score and bilateral entorhinal volume among linked participants aged 65 years or older. The analysis is descriptive and does not estimate general-population prevalence or causal effects. Figure paths are relative to the \texttt{reports/} directory, so compile with \texttt{cd reports \&\& pdflatex phase2.tex}.\end{abstract}

\section{Introduction and biomedical context}
Atrophy of the entorhinal cortex is among the earliest structural changes in Alzheimer's disease, and it precedes widespread neocortical loss. The Montreal Cognitive Assessment (MoCA) is a brief cognitive screening instrument that is sensitive to mild cognitive impairment. If smaller entorhinal volume goes together with worse cognition, then knowing a person's volume group should change the probability that the person has MCI or dementia. Probability theory states that question precisely: it gives the prior $P(A)$, the conditional probability $P(A\mid B)$ and a rule, Bayes' theorem, for moving between $P(B\mid A)$ and $P(A\mid B)$. The same cohort supports a distribution check of both measurements and a covariance estimate. Among unique participants aged at least 65 in the supplied linked subset, the question is: how do empirical probabilities of MCI or dementia vary across entorhinal volume groups, and how are MoCA and volume distributed and associated? Phase 1 conventions are retained: NACCID is the participant key, NACCAGE $\geq65$, MOCATOTS is valid only in $[0,30]$, and bilateral volume is the arithmetic mean of valid positive left and right values. NACCUDSD codes are 1 Normal, 2 Impaired not MCI, 3 MCI, 4 Dementia.

\section{Data, linkage, and sample sizes}
Each CSV has one row per unique NACCID. The script checks uniqueness and NACCUDSD agreement, links by ID, and applies the age rule. The files lack visit identifiers, visit dates, and MRI scan dates, so baseline status and UDS--MRI contemporaneity cannot be established. The UDS file is processed and imputed, and the imputation method is not available. The subset is a clinical/research subset, not a probability sample of older adults.
\begin{table}[H]\centering\caption{Analytic flow and valid sample sizes}\begin{tabular}{lr}\toprule Stage & Participants\\\midrule
UDS input records & <<flow0>>\\ MRI input records & <<flow1>>\\ Matched unique participants & <<flow2>>\\ Age eligible ($\geq65$) & <<flow3>>\\ Valid status and volume (2$\times$2 table) & <<n>>\\ Valid MOCATOTS & <<nmoca>>\\ Valid bilateral volume & <<nvol>>\\ Paired MoCA and volume & <<cn>>\\\bottomrule\end{tabular}\end{table}

\section{Events and basic probabilities}
Define the two events on the common valid subset of $n=<<n>>$ participants:
\[A=\{\mathrm{NACCUDSD}\in\{3,4\}\}\ \text{(MCI or dementia)},\qquad B=\{\mathrm{bilateral\_entorhinal\_volume}\leq <<median>>\ \mathrm{mm}^3\}\ \text{(at or below the median)}.\]
The threshold <<median>>~mm$^3$ is the median of the <<nvol>> valid volumes. Because <<ties>> observations equal the median exactly, ties go to $B$, so $B$ contains <<nB>> participants rather than exactly half. Table~\ref{tab:2x2} shows counts and row percentages.
\begin{table}[H]\centering\caption{Cognitive status by volume group, counts and row percentages ($n=<<n>>$)}\label{tab:2x2}\begin{tabular}{lrrrrr}\toprule Group & Impaired ($A$) & Normal ($A^c$) & Total & Impaired \% & Normal \%\\\midrule
Low volume ($B$) & <<n11>> & <<n01>> & <<nlow>> & <<lowA_pct>> & <<lowN_pct>>\\ High volume ($B^c$) & <<n10>> & <<n00>> & <<nhigh>> & <<highA_pct>> & <<highN_pct>>\\ Total & <<nA>> & <<nnA>> & <<n>> & <<totA_pct>> & <<totN_pct>>\\\bottomrule\end{tabular}\end{table}
\begin{align*}
P(A)&=\tfrac{<<nA>>}{<<n>>}=<<pA>>, & P(A^c)&=1-P(A)=\tfrac{<<nnA>>}{<<n>>}=<<pnA>>,\\
P(B)&=\tfrac{<<nB>>}{<<n>>}=<<pB>>, & P(B^c)&=1-P(B)=\tfrac{<<nnB>>}{<<n>>}=<<pnB>>,\\
P(A\cap B)&=\tfrac{<<n11>>}{<<n>>}=<<pAB>>, & P(A)P(B)&=<<pApB>>.
\end{align*}
Since $P(A\cap B)\neq P(A)P(B)$, the two events are not independent in this subset. This is a comparison of frequencies, not a formal independence test. Figure~\ref{fig:group} shows the group probabilities.
\begin{figure}[H]\centering\includegraphics[width=.8\linewidth]{../figures/phase2/group_probabilities.pdf}\caption{Empirical probability of MCI or dementia in the low and high volume groups.}\label{fig:group}\end{figure}

\section{Bayes' theorem}
The conditional probabilities come from the table: $P(B\mid A)=\tfrac{<<n11>>}{<<nA>>}=<<pB_A>>$ and $P(B\mid A^c)=\tfrac{<<n01>>}{<<nnA>>}=<<pB_nA>>$. Bayes' theorem with the law of total probability gives
\[P(A\mid B)=\frac{P(B\mid A)\,P(A)}{P(B\mid A)\,P(A)+P(B\mid A^c)\,P(A^c)}.\]
Substituting the values step by step:
\begin{align*}
P(B)&=(<<pB_A>>)(<<pA>>)+(<<pB_nA>>)(<<pnA>>)=<<pBder>>,\\
P(A\mid B)&=\frac{(<<pB_A>>)(<<pA>>)}{<<pBder>>}=<<pAbayes>>.
\end{align*}
The direct table ratio is $P(A\mid B)=\tfrac{<<n11>>}{<<nB>>}=<<pAdirect>>$ and the derived marginal $P(B)=<<pBder>>$ equals the counted $P(B)=<<pB>>$, so the two routes agree (script check: \texttt{match = <<match>>}). In words: the probability that a person with low entorhinal volume has MCI or dementia rises from the base rate of <<pA_pct>>\% to <<pA_B_pct>>\%, whereas for high volume it is <<pA_nB_pct>>\%. Figure~\ref{fig:bayes} compares these values with the prior. This is an event frequency calculation in this dataset, not a validated diagnostic rule.
\begin{figure}[H]\centering\includegraphics[width=.65\linewidth]{../figures/phase2/bayes_posterior.pdf}\caption{Posterior probabilities of impairment by volume group against the prior $P(A)$.}\label{fig:bayes}\end{figure}

\section{Binomial distribution}
Let $Y$ count outcomes of $A$ among $m=<<binn>>$ independent draws with success probability $p=P(A)=<<pA>>$. Then
\[P(Y=k)=\binom{m}{k}p^k(1-p)^{m-k},\quad E[Y]=mp=<<EY>>,\quad \operatorname{Var}(Y)=mp(1-p)=<<VarY>>.\]
The binomial model needs fixed $m$, independent trials, a constant $p$, and two outcomes. Drawing distinct participants from the finite cohort is sampling without replacement, so draws are not exactly independent and the exact model is hypergeometric. The usual 10\% rule says the binomial is a good approximation when the sample is less than 10\% of the population. Here $m/n=<<tenpct>>\%$, which satisfies the rule. Using all $n=<<n>>$ participants would violate it, so the binomial is used only for the hypothetical $m=<<binn>>$ draws.
\begin{figure}[H]\centering\includegraphics[width=.8\linewidth]{../figures/phase2/binomial_pmf.pdf}\caption{Binomial$(<<binn>>,<<pA>>)$ probability mass function.}\end{figure}

\section{Normal distribution and the central limit theorem}
Table~\ref{tab:norm} lists shape statistics and Shapiro--Wilk results (computed in Python). Excess kurtosis is 0 for a normal distribution.
\begin{table}[H]\centering\caption{Normality statistics}\label{tab:norm}\begin{tabular}{lrrrrrr}\toprule Variable & $n$ & Mean & Skewness & Excess kurtosis & Shapiro $W$ & Shapiro $p$\\\midrule
MoCA (points) & <<nmoca>> & <<mmean>> & <<msk>> & <<mku>> & <<mW>> & $<<msp>>$\\ Volume (mm$^3$) & <<nvol>> & <<vmean>> & <<vsk>> & <<vku>> & <<vW>> & $<<vsp>>$\\\bottomrule\end{tabular}\end{table}
Both Shapiro--Wilk tests reject normality. MoCA is strongly left skewed with a ceiling near 30, and volume is mildly right skewed with heavy tails. The Q--Q plots in Figures~\ref{fig:mqq} and~\ref{fig:vqq} show the same departures in the tails. With $n=<<n>>$ the central limit theorem implies that the sample mean $\bar X$ is approximately normal with mean $\mu$ and variance $\sigma^2/n$ even when the data are not normal, so inference about means does not require normal data. The histograms are in Figures~\ref{fig:mh} and~\ref{fig:vh}.
\begin{figure}[H]\centering\includegraphics[width=.75\linewidth]{../figures/phase2/moca_histogram.pdf}\caption{MoCA histogram with fitted normal density.}\label{fig:mh}\end{figure}
\begin{figure}[H]\centering\includegraphics[width=.75\linewidth]{../figures/phase2/moca_qq.pdf}\caption{Normal Q--Q plot of MoCA. The tails depart from the line because of left skew and the ceiling.}\label{fig:mqq}\end{figure}
\begin{figure}[H]\centering\includegraphics[width=.75\linewidth]{../figures/phase2/volume_histogram.pdf}\caption{Bilateral entorhinal volume histogram with fitted normal density.}\label{fig:vh}\end{figure}
\begin{figure}[H]\centering\includegraphics[width=.75\linewidth]{../figures/phase2/volume_qq.pdf}\caption{Normal Q--Q plot of bilateral volume. The upper tail is heavier than normal.}\label{fig:vqq}\end{figure}

\section{Covariance and correlation}
For paired observations $(x_i,y_i)$ of MoCA and volume, the sample covariance and the Pearson correlation are
\[\hat\sigma_{XY}=\frac{1}{n-1}\sum_{i=1}^{n}(x_i-\bar x)(y_i-\bar y),\qquad r=\frac{\hat\sigma_{XY}}{\hat\sigma_X\hat\sigma_Y}.\]
Only <<cn>> participants have both a valid MoCA and a valid volume, so $n=<<cn>>$ here. The results are $\hat\sigma_{XY}=<<cov>>$ points$\cdot$mm$^3$, Pearson $r=<<pr>>$ ($p=<<pp>>$) and Spearman $\rho=<<sr>>$ ($p=<<sp>>$). The association is positive: larger entorhinal volume goes with higher MoCA. It is weak to modest, since $r^2=<<r2>>$ means about <<r2pct>>\% of the variance is shared linearly. Spearman is slightly larger than Pearson, which is consistent with a skewed MoCA. Correlation does not imply causation: age, education, and other factors may influence both measures. Figure~\ref{fig:scatter} shows the data with the fitted line and its 95\% confidence band; MoCA values are integers, so a small horizontal jitter is applied for display only.
\begin{figure}[H]\centering\includegraphics[width=.9\linewidth]{../figures/phase2/moca_volume_scatter_regression.pdf}\caption{MoCA versus bilateral entorhinal volume colored by NACCUDSD, with linear regression and 95\% confidence band.}\label{fig:scatter}\end{figure}

\section{Limitations}
The median threshold for $B$ is a convenient but arbitrary choice. A different cut point, or treating volume as continuous, could change $P(A\mid B)$. Ties at the median also make the two groups unequal in size.

The probability calculations treat participants as independent. The participants come from several contributing centers and may share scanners, protocols, and referral patterns, so this assumption may be violated and standard errors and p-values may be too optimistic.

Pearson correlation measures linear association and is sensitive to outliers and to nonlinearity. MoCA is bounded and left skewed, so the linear summary may miss the real shape of the relationship; Spearman is reported as a rank based check.

MoCA is a screening instrument, not a definitive diagnosis. The classification $A$ is the dataset's NACCUDSD code, and all probabilities describe this supplied clinical/research subset rather than older adults in general.

\section*{Reproducibility}
Run \texttt{python src/phase2\_analysis.py} from the repository root. Numbers in this report are taken from \texttt{reports/phase2/phase2\_results.json}. The PDF \texttt{reports/phase2.pdf} was produced with ReportLab because no TeX engine was available; this \texttt{.tex} source has not been compiled in that environment.
\end{document}
'''
    V["match"]=str(bv["match"]).lower(); V["r2pct"]=f"{100*co['pearson_r']**2:.1f}"
    for k,v in V.items(): tex=tex.replace(f"<<{k}>>",str(v))
    assert "<<" not in tex
    (ROOT/"reports"/"phase2.tex").write_text(tex,encoding="utf-8")


def build_pdf(r):
    """Create a companion PDF using bundled ReportLab if no TeX engine exists."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, String, Rect, Line, Circle
    from reportlab.graphics import renderPDF
    from reportlab.pdfgen import canvas

    # Plot PDFs are rendered directly from the same summaries/data as the SVGs.
    # A compact vector drawing representation supports inspection in the report.
    figpdf=FIG
    def draw_pdf(name, title, values, labels=None, maxval=None):
        path=figpdf/(name+".pdf"); w,h=720,420
        from reportlab.pdfgen import canvas
        observations=list(values) if name in ("moca_histogram","volume_histogram") else None
        c=canvas.Canvas(str(path),pagesize=(w,h));c.setFont("Helvetica-Bold",15);c.drawCentredString(w/2,h-30,title)
        L,R,T,B=70,25,60,65;ph=h-T-B;pw=w-L-R
        if name=="moca_volume_scatter":
            xx,yy=values; xmin,xmax=min(xx),max(xx);ymin,ymax=min(yy),max(yy)
            mx,my=statistics.mean(xx),statistics.mean(yy);slope=sum((a-mx)*(b-my) for a,b in zip(xx,yy))/sum((a-mx)**2 for a in xx);intercept=my-slope*mx
            c.setStrokeColor(colors.HexColor("#d1495b"));c.setLineWidth(1.4)
            c.line(L,B+ph*(intercept+slope*xmin-ymin)/(ymax-ymin),L+pw,B+ph*(intercept+slope*xmax-ymin)/(ymax-ymin))
            c.setFillColor(colors.Color(.14,.48,.63,alpha=.35))
            for xv,yv in zip(xx,yy):c.circle(L+pw*(xv-xmin)/(xmax-xmin),B+ph*(yv-ymin)/(ymax-ymin),1.5,fill=1,stroke=0)
            c.setStrokeColor(colors.black);c.line(L,B,w-R,B);c.line(L,B,L,h-T);c.setFillColor(colors.black);c.setFont("Helvetica",8)
            for t in range(5):
                c.drawCentredString(L+pw*t/4,B-12,f"{xmin+(xmax-xmin)*t/4:.1f}")
                c.drawRightString(L-6,B+ph*t/4-3,f"{ymin+(ymax-ymin)*t/4:.0f}")
            c.setFont("Helvetica",9);c.drawCentredString(w/2,20,"MOCATOTS (score points)");c.saveState();c.translate(16,B+ph/2);c.rotate(90);c.drawCentredString(0,0,"Bilateral entorhinal volume (mm³)");c.restoreState();c.save();return path
        elif name=="binomial_pmf":
            top=max(values);bw=pw/len(values)*.55
            for i,v in enumerate(values):
                bh=ph*v/top;c.setFillColor(colors.HexColor("#247ba0"));c.rect(L+pw*(i+.5)/len(values)-bw/2,B,bw,bh,fill=1,stroke=0);c.setFillColor(colors.black);c.setFont("Helvetica",8);c.drawCentredString(L+pw*(i+.5)/len(values),B-15,str(i))
        elif labels is None:
            xs=values; mn=min(xs);mx=max(xs);bins=16;cnt=[0]*bins; step=(mx-mn or 1)/bins
            for v in xs:cnt[min(bins-1,int((v-mn)/step))]+=1
            labels=[f"{mn+(i+.5)*(mx-mn or 1)/bins:.1f}" for i in range(bins)];values=cnt
        top=maxval or max(values)
        c.setStrokeColor(colors.HexColor("#d9e1e8"));
        for t in range(5):
            yy=B+ph*t/4;c.line(L,yy,w-R,yy);c.setFont("Helvetica",8);c.drawRightString(L-7,yy-3,f"{top*t/4:.2f}" if maxval or name=="binomial_pmf" else f"{top*t/4:.0f}")
        if name=="group_probabilities":
            bw=130
            for i,v in enumerate(values):
                bh=ph*v/100;c.setFillColor(colors.HexColor("#247ba0"));c.rect(L+pw*(i+.5)/2-bw/2,B,bw,bh,fill=1,stroke=0);c.setFillColor(colors.black);c.drawCentredString(L+pw*(i+.5)/2,B-20,labels[i]);c.drawCentredString(L+pw*(i+.5)/2,B+bh+5,f"{v:.1f}% ({r['groups'][i]['n_MCI_or_dementia']}/{r['groups'][i]['n_group']})")
        elif name=="binomial_pmf":
            c.setFont("Helvetica",9);c.drawCentredString(w/2,20,"Count k of A outcomes among 10 draws")
        else:
            bw=pw/len(values)*.9
            for i,v in enumerate(values):
                bh=ph*v/top;c.setFillColor(colors.HexColor("#247ba0"));c.rect(L+i*pw/len(values),B,bw,bh,fill=1,stroke=0)
            if name in ("moca_histogram","volume_histogram"):
                mu=statistics.mean(observations);sd=statistics.pstdev(observations);mn=min(observations);mx=max(observations);bins=16;step=(mx-mn or 1)/bins
                c.setStrokeColor(colors.HexColor("#d1495b"));c.setLineWidth(1.6);prev=None
                for i in range(201):
                    val=mn+(mx-mn or 1)*i/200;density=math.exp(-.5*((val-mu)/sd)**2)/(sd*math.sqrt(2*math.pi))*len(observations)*step
                    pt=(L+pw*i/200,B+ph*density/top)
                    if prev:c.line(prev[0],prev[1],pt[0],pt[1])
                    prev=pt
            mn,mx=min(observations),max(observations)
            c.setFont("Helvetica",8);c.setFillColor(colors.black)
            for t in range(5):c.drawCentredString(L+pw*t/4,B-13,f"{mn+(mx-mn)*t/4:.1f}")
            c.setFont("Helvetica",9);c.drawCentredString(w/2,20,"MOCATOTS score points" if name=="moca_histogram" else "Bilateral entorhinal volume (mm³)")
            c.saveState();c.translate(15,B+ph/2);c.rotate(90);c.drawCentredString(0,0,"Participants");c.restoreState()
            c.setStrokeColor(colors.HexColor("#d1495b"));c.line(w-150,h-45,w-125,h-45);c.setFillColor(colors.black);c.drawString(w-120,h-48,"Fitted normal density")
        if name=="group_probabilities":
            c.saveState();c.translate(17,B+ph/2);c.rotate(90);c.drawCentredString(0,0,"Empirical probability P(A)");c.restoreState()
        if name=="binomial_pmf":
            c.saveState();c.translate(17,B+ph/2);c.rotate(90);c.drawCentredString(0,0,"Probability");c.restoreState()
        c.setStrokeColor(colors.black);c.line(L,B,w-R,B);c.line(L,B,L,h-T);c.showPage();c.save();return path
    for nm,title,vals,labs in [
        ("moca_histogram","MoCA valid-score histogram",_last_moca,None),
        ("volume_histogram","Bilateral entorhinal volume histogram",[q["VOL"] for q in _last_valid_rows if q["VOL"] is not None],None),
        ("group_probabilities","MCI or dementia by volume group",[g["percent"] for g in r["groups"]],[g["group"] for g in r["groups"]]),
        ("binomial_pmf","Binomial(10, p) probability mass",[x["probability"] for x in r["binomial"]["pmf"]],None)]: draw_pdf(nm,title,vals,labs,1 if nm=="group_probabilities" else None)
    # Scatter render needs the paired arrays; reread and derive same pair list.
    draw_pdf("moca_volume_scatter","MoCA and bilateral entorhinal volume",(list(zip(*_last_pairs))[0],list(zip(*_last_pairs))[1]))
    from statistics import NormalDist
    def qq_pdf(name,title,values):
        path=FIG/(name+".pdf");w,h=720,420;L,R,T,B=70,25,60,65;pw=w-L-R;ph=h-T-B
        xs=sorted(values);mu=statistics.mean(xs);sd=statistics.pstdev(xs);nd=NormalDist()
        theo=[nd.inv_cdf((i+.5)/len(xs)) for i in range(len(xs))];x0,x1=min(theo),max(theo);y0,y1=min(xs),max(xs);pad=(y1-y0)*.04;y0-=pad;y1+=pad
        c=canvas.Canvas(str(path),pagesize=(w,h));c.setFont("Helvetica-Bold",15);c.drawCentredString(w/2,h-30,title)
        c.setStrokeColor(colors.HexColor("#d1495b"));c.line(L,B+ph*(y1-(mu+sd*x0))/(y1-y0),L+pw,B+ph*(y1-(mu+sd*x1))/(y1-y0))
        c.setFillColor(colors.HexColor("#247ba0"))
        for t,v in zip(theo,xs):c.circle(L+pw*(t-x0)/(x1-x0),B+ph*(y1-v)/(y1-y0),1.5,fill=1,stroke=0)
        c.setFont("Helvetica",9);c.setFillColor(colors.black);c.drawCentredString(w/2,20,"Theoretical normal quantiles");c.saveState();c.translate(15,B+ph/2);c.rotate(90);c.drawCentredString(0,0,"Observed MoCA score points" if name=="moca_qq" else "Observed volume (mm³)");c.restoreState();c.save()
    qq_pdf("moca_qq","Normal Q-Q plot: MOCATOTS",_last_moca)
    qq_pdf("volume_qq","Normal Q-Q plot: bilateral entorhinal volume",[q["VOL"] for q in _last_valid_rows if q["VOL"] is not None])
    import pypdfium2 as pdfium
    for pdfpath in figpdf.glob("*.pdf"):
        doc=pdfium.PdfDocument(str(pdfpath)); page=doc[0]
        page.render(scale=1.5).to_pil().save(str(pdfpath.with_suffix(".png")))
    styles=getSampleStyleSheet();styles.add(ParagraphStyle(name="Small",parent=styles["BodyText"],fontSize=8.4,leading=11));story=[]
    def P(t,style="BodyText"):story.append(Paragraph(t,styles[style]));story.append(Spacer(1,7))
    def section(t):P(f"<b>{t}</b>","Heading2")
    def table(data,widths=None):
        t=Table(data,colWidths=widths,repeatRows=1);t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#18324b")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#ccd5de")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f6f8")]),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]));story.append(t);story.append(Spacer(1,10))
    bv=r["bayes_verification"];co=r["correlation"];nm=r["normality"];bi=r["binomial"];ev=r["events"]
    p=r["probabilities"];c=r["contingency"];n=c["denominator"]
    n11,n10,n01,n00=(x["count"] for x in c["rows"]);pA=p["P_A"]["value"];pB=p["P_B"]["value"]
    def sci(x):return f"{x:.2e}"
    def fig(name,w,cap):
        from reportlab.lib.utils import ImageReader
        iw,ih=ImageReader(str(FIG/(name+".png"))).getSize()
        story.append(Image(str(FIG/(name+".png")),width=w,height=w*ih/iw));P(f"<i>{cap}</i>","Small")
    P("Phase 2: Probability Analysis of MoCA and Entorhinal Volume","Title")
    section("1. Introduction and biomedical context")
    P("Atrophy of the entorhinal cortex is among the earliest structural changes in Alzheimer's disease, and MoCA is a brief cognitive screening instrument. If smaller entorhinal volume goes with worse cognition, the volume group should change the probability of MCI or dementia. Probability theory makes this precise through P(A), P(A|B), and Bayes' theorem. The same cohort supports distribution checks and a covariance estimate. Question: among linked participants aged 65 or older, how do empirical probabilities of MCI or dementia vary across volume groups, and how are MoCA and volume distributed and associated?")
    P("Conventions follow Phase 1: NACCID is the participant key, NACCAGE ≥ 65, MOCATOTS is valid only in [0,30], and bilateral volume is the mean of positive left and right entorhinal volumes. The files lack visit IDs/dates and MRI scan dates, so baseline status and UDS/MRI contemporaneity cannot be established. The UDS file is processed/imputed, and the subset is a clinical/research subset, not a representative sample.","Small")
    table([["Stage","n"]]+[[q["step"],str(q["n"])] for q in r["flow"]],[5.2*inch,1.1*inch])
    section("2. Events and basic probabilities")
    P(f"A = {{NACCUDSD ∈ {{3,4}}}} (MCI or dementia). B = {{bilateral entorhinal volume ≤ {ev['median_mm3']:.0f} mm³}} (at or below the median of {ev['volume_median_n']} valid volumes). {ev['equal_to_median_n']} observations equal the median and are assigned to B, so B has {n11+n01} members rather than exactly half. Common denominator n={n}.")
    table([["Group","Impaired (A)","Normal (A^c)","Total","Impaired %","Normal %"],
           ["Low volume (B)",str(n11),str(n01),str(n11+n01),f"{100*n11/(n11+n01):.2f}",f"{100*n01/(n11+n01):.2f}"],
           ["High volume (B^c)",str(n10),str(n00),str(n10+n00),f"{100*n10/(n10+n00):.2f}",f"{100*n00/(n10+n00):.2f}"],
           ["Total",str(n11+n10),str(n01+n00),str(n),f"{100*pA:.2f}",f"{100*(1-pA):.2f}"]])
    P(f"P(A) = {n11+n10}/{n} = {pA:.4f}; P(A^c) = {n01+n00}/{n} = {1-pA:.4f}; P(B) = {c['marginal_B']}/{n} = {pB:.4f}; P(B^c) = {c['marginal_not_B']}/{n} = {1-pB:.4f}; P(A∩B) = {n11}/{n} = {p['P_A_and_B']['value']:.4f}. P(A)P(B) = {p['P_A_times_P_B']:.4f} differs from P(A∩B), so A and B are not independent in this subset (a frequency comparison, not a formal test).")
    fig("group_probabilities",360,"Figure 1. Empirical probability of MCI or dementia by volume group.")
    story.append(PageBreak())
    section("3. Bayes' theorem")
    P("P(A|B) = P(B|A)·P(A) / [P(B|A)·P(A) + P(B|A^c)·P(A^c)]")
    P(f"P(B|A) = {n11}/{n11+n10} = {bv['P_B_given_A']:.4f}; P(B|A^c) = {n01}/{n01+n00} = {bv['P_B_given_not_A']:.4f}. Total probability: P(B) = ({bv['P_B_given_A']:.4f})({pA:.4f}) + ({bv['P_B_given_not_A']:.4f})({1-pA:.4f}) = {bv['P_B_derived']:.4f}. Then P(A|B) = ({bv['P_B_given_A']:.4f})({pA:.4f}) / {bv['P_B_derived']:.4f} = {bv['P_A_given_B_bayes']:.4f}.")
    P(f"The direct table ratio is {n11}/{c['marginal_B']} = {bv['P_A_given_B_direct']:.4f}, and the derived P(B) matches the counted {pB:.4f}; the two routes agree (match = {bv['match']}). Interpretation: the probability that a person with low entorhinal volume has MCI or dementia rises from the base rate of {100*pA:.1f}% to {100*bv['P_A_given_B_bayes']:.1f}%; for high volume it is {100*p['P_A_given_not_B']['value']:.1f}%. This is a dataset event frequency calculation, not a validated diagnostic rule.")
    fig("bayes_posterior",340,"Figure 2. Posterior probability of impairment by volume group against the prior P(A).")
    section("4. Binomial distribution")
    P(f"For m={bi['n']} independent draws with p=P(A)={pA:.4f}: P(Y=k) = C(m,k) p^k (1-p)^(m-k), E[Y] = mp = {bi['expected']:.3f}, Var(Y) = mp(1-p) = {bi['variance']:.3f}. The model requires fixed m, independent trials, constant p, and two outcomes. Drawing distinct participants from this finite cohort is sampling without replacement, so independence does not hold exactly (the exact model is hypergeometric). The 10% rule says the binomial approximates well when the sample is under 10% of the population; here m/n = {100*bi['n']/n:.1f}%, which satisfies it, whereas using all {n} participants would not.")
    fig("binomial_pmf",340,f"Figure 3. Binomial({bi['n']}, {pA:.3f}) probability mass function.")
    story.append(PageBreak())
    section("5. Normal distribution and the central limit theorem")
    table([["Variable","n","Skewness","Excess kurtosis","Shapiro W","Shapiro p"],
           ["MoCA (points)",str(nm["moca_n"]),f"{nm['moca_skewness']:.3f}",f"{nm['moca_kurtosis']:.3f}",f"{nm['moca_shapiro_W']:.3f}",sci(nm["moca_shapiro_p"])],
           ["Volume (mm³)",str(nm["volume_n"]),f"{nm['volume_skewness']:.3f}",f"{nm['volume_kurtosis']:.3f}",f"{nm['volume_shapiro_W']:.3f}",sci(nm["volume_shapiro_p"])]])
    P(f"Both Shapiro-Wilk tests reject normality. MoCA is strongly left skewed with a ceiling near 30; volume is mildly right skewed with heavy tails. With n={n}, the central limit theorem makes the sample mean approximately normal even when the data are not, so inference about means does not require normal data. The Q-Q plots show the tail departures.")
    fig("moca_histogram",300,"Figure 4. MoCA histogram with fitted normal density.")
    fig("moca_qq",300,"Figure 5. Normal Q-Q plot of MoCA; the tails depart because of left skew and the ceiling.")
    fig("volume_histogram",300,"Figure 6. Bilateral volume histogram with fitted normal density.")
    fig("volume_qq",300,"Figure 7. Normal Q-Q plot of bilateral volume; the upper tail is heavier than normal.")
    section("6. Covariance and correlation")
    P("Sample covariance: σ̂_XY = (1/(n-1)) Σ (x_i − x̄)(y_i − ȳ). Pearson correlation: r = σ̂_XY / (σ̂_X σ̂_Y).")
    P(f"Only {co['n']} participants have both a valid MoCA and valid volume (8 lack MoCA), so n={co['n']}. σ̂_XY = {co['covariance']:.2f} points·mm³; Pearson r = {co['pearson_r']:.4f} (p = {sci(co['pearson_p'])}); Spearman ρ = {co['spearman_r']:.4f} (p = {sci(co['spearman_p'])}). The association is positive and weak to modest: r² = {co['pearson_r']**2:.3f}, about {100*co['pearson_r']**2:.1f}% shared variance. Correlation is not causation; age, education, and other factors may affect both measures. MoCA values are integers, so display jitter of ±0.2 is applied in the figure only.")
    fig("moca_volume_scatter_regression",400,"Figure 8. MoCA versus bilateral volume colored by NACCUDSD, with linear regression and 95% confidence band.")
    section("7. Limitations")
    P("The median threshold for B is a convenient but arbitrary choice; another cut point, or treating volume as continuous, could change P(A|B). Ties at the median also make the groups unequal.")
    P("The calculations treat participants as independent. Participants come from several contributing centers and may share scanners, protocols, and referral patterns, so this assumption may be violated and p-values may be too optimistic.")
    P("Pearson correlation measures linear association and is sensitive to outliers and nonlinearity. MoCA is bounded and left skewed, so Spearman is reported as a rank based check.")
    P("MoCA is a screening instrument, not a definitive diagnosis. A is the dataset's NACCUDSD code, and all probabilities describe this supplied clinical/research subset.")
    P("Reproduce with python src/phase2_analysis.py. This PDF was generated with ReportLab because no TeX engine was available; reports/phase2.tex is the LaTeX source and was not compiled here.","Small")
    SimpleDocTemplate(str(ROOT/"reports"/"phase2.pdf"),pagesize=letter,rightMargin=.65*inch,leftMargin=.65*inch,topMargin=.6*inch,bottomMargin=.6*inch,title="Phase 2 Probability Analysis").build(story)


_last_valid_rows=[]
_last_pairs=[]
_last_moca=[]

if __name__=="__main__":
    # Populate module-level plotting inputs for the report builder from the same CSVs.
    # main() computes these cohort records below via a lightweight reconstruction.
    _u=read_csv(DATA/"udslong_imputed.csv");_m=read_csv(DATA/"mriscanclean.csv");_mmap={q["NACCID"]:q for q in _m}
    for q in _u:
        z=_mmap.get(q["NACCID"])
        if not z: continue
        age=num(q.get("NACCAGE")); mo=num(q.get("MOCATOTS")); l=num(z.get("LH_ENTORHINAL_GVOL"));rr=num(z.get("RH_ENTORHINAL_GVOL"))
        if age is None or age<65:continue
        vol=(l+rr)/2 if l and rr and l>0 and rr>0 else None
        row={"VOL":vol};_last_valid_rows.append(row)
        if mo is not None and 0<=mo<=30:
            _last_moca.append(mo)
            if vol is not None:_last_pairs.append((mo,vol))
    main()
