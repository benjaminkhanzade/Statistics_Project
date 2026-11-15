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
    csv_write(OUT/"analytic_flow.csv",flow,["step","n"])
    csv_write(OUT/"contingency_2x2.csv",[{"A":"yes","B":"yes","count":n11,"denominator":n},{"A":"yes","B":"no","count":n10,"denominator":n},{"A":"no","B":"yes","count":n01,"denominator":n},{"A":"no","B":"no","count":n00,"denominator":n}], ["A","B","count","denominator"])
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

    write_report_tex(result)
    try: build_pdf(result)
    except ImportError as e: print(f"ReportLab PDF build skipped: {e}")
    print(json.dumps({"linked":linked,"age65plus":len(eligible),"median_mm3":median,"two_by_two":[n11,n10,n01,n00],"P_A":pA,"P_A_given_B":pA_B,"P_A_given_not_B":pA_notB,"covariance":cov,"r":corr,"figures":len(list(FIG.iterdir()))},indent=2))


def write_report_tex(r):
    c=r["contingency"]; p=r["probabilities"]; e=r["events"]; g=r["groups"]; d=r["continuous"]; a=r["association"]
    tex=rf'''\documentclass[11pt]{{article}}
\usepackage[margin=0.85in]{{geometry}}
\usepackage{{booktabs,graphicx,amsmath,hyperref,caption,float}}
\title{{Phase 2: Descriptive Probability Analysis of MoCA and Entorhinal Volume}}
\author{{Statistics Project -- NACC UDS + MRI subset}}
\date{{}}
\begin{{document}}\maketitle
\begin{{abstract}}This report describes empirical probabilities and distributions among supplied, linked participants aged 65 years or older. It examines dataset-coded cognitive status and bilateral entorhinal volume. The analysis is descriptive and does not estimate general-population prevalence or causal effects.\end{{abstract}}
\section{{Research question and Phase 1 continuity}}
Among unique participants aged at least 65 in the supplied linked NACC UDS and MRI subset, how do empirical probabilities of MCI or dementia vary across groups defined by bilateral entorhinal volume, and what are the distributions and linear association of MoCA score and volume? Phase 1's conventions are retained: NACCID as participant key; NACCAGE $\geq65$; MOCATOTS valid only in [0,30], without rounding or clipping; EDUC=99 unknown; and bilateral MRI measurement as the arithmetic mean of valid positive left and right values. NACCUDSD is coded 1=Normal, 2=Impaired not MCI, 3=MCI, and 4=Dementia.
\section{{Data, unit, linkage, and limits}}
Each CSV contains a single supplied row per unique NACCID. The script verifies uniqueness and agreement of NACCUDSD across files, links by ID, then applies the age rule. The main analysis retains this one record per participant. The files lack visit identifiers/dates and MRI scan dates; therefore this record cannot be established as a baseline, nor can contemporaneous UDS--MRI measurement be established. The UDS file is processed/imputed, but the imputation procedure and original missingness mask are unavailable; no blank cells do not prove that original observations were complete. The supplied subset is a clinical/research subset, not a probability sample of older adults generally.
\begin{{table}}[H]\centering\caption{{Analytic flow and valid sample sizes}}\begin{{tabular}}{{lr}}\toprule Stage & Participants\\\midrule
UDS input records & {r['flow'][0]['n']}\\ MRI input records & {r['flow'][1]['n']}\\ Matched unique participants & {r['flow'][2]['n']}\\ Age eligible ($\geq65$) & {r['flow'][3]['n']}\\ 2$\times$2 valid status and volume & {c['denominator']}\\ Valid MOCATOTS & {d['MOCATOTS_points']['n']}\\ Valid bilateral volume & {d['bilateral_entorhinal_volume_mm3']['n']}\\ Paired MoCA and volume & {a['n']}\\\bottomrule\end{{tabular}}\end{{table}}
\section{{Events and empirical probabilities}}
For each eligible participant record $r$, define $A(r)=1$ when NACCUDSD is 3 or 4 (MCI or dementia), and $B(r)=1$ when bilateral entorhinal volume is at or below the eligible cohort's linearly interpolated median, {e['volume_median_n']} valid measures, {e['B']}. Ties are assigned to $B=1$; {e['equal_to_median_n']} observations equal the threshold. $A$ is the supplied UDS classification, not a new clinical diagnosis. Both events use the common valid subset of $n={c['denominator']}$. Table~\ref{{tab:2x2}} gives counts.
\begin{{table}}[H]\centering\caption{{Joint frequencies for A and B (common denominator $n={c['denominator']}$)}}\label{{tab:2x2}}\begin{{tabular}}{{lrrr}}\toprule & $B=1$ & $B=0$ & Total\\\midrule $A=1$ & {c['rows'][0]['count']} & {c['rows'][1]['count']} & {c['marginal_A']}\\ $A=0$ & {c['rows'][2]['count']} & {c['rows'][3]['count']} & {c['marginal_not_A']}\\ Total & {c['marginal_B']} & {c['marginal_not_B']} & {c['denominator']}\\\bottomrule\end{{tabular}}\end{{table}}
\[P(A)=\frac{{{c['marginal_A']}}}{{{c['denominator']}}}={p['P_A']['value']:.4f},\quad P(B)=\frac{{{c['marginal_B']}}}{{{c['denominator']}}}={p['P_B']['value']:.4f},\quad P(A\cap B)=\frac{{{c['rows'][0]['count']}}}{{{c['denominator']}}}={p['P_A_and_B']['value']:.4f}.\]
\[P(A\mid B)=\frac{{{c['rows'][0]['count']}}}{{{c['marginal_B']}}}={p['P_A_given_B']['value']:.4f};\quad P(A\mid B^c)=\frac{{{c['rows'][1]['count']}}}{{{c['marginal_not_B']}}}={p['P_A_given_not_B']['value']:.4f}.\]
Among participants with $A=1$, the empirical probability of belonging to the at-or-below-median volume group is $P(B\mid A)={c['rows'][0]['count']}/{c['marginal_A']}={p['P_B_given_A']['value']:.4f}$. The observed conditional probability differs from the marginal; conditioning describes an empirical contrast and does not imply a causal effect.
\section{{Group comparison and independence discussion}}
The empirical probability of A is {g[0]['n_MCI_or_dementia']}/{g[0]['n_group']}={g[0]['probability']:.4f} ({g[0]['percent']:.1f}\%) at/below the volume median, and {g[1]['n_MCI_or_dementia']}/{g[1]['n_group']}={g[1]['probability']:.4f} ({g[1]['percent']:.1f}\%) above it. The denominator in each case is participants with age eligibility, valid bilateral positive volume, and valid NACCUDSD. Figure~\ref{{fig:group}} shows this comparison. The four-level status breakdown includes only six participants coded 2 (Impaired, not MCI) among the age-eligible cohort; detailed percentages for this small category are not emphasized.
Empirical independence would suggest $P(A\cap B)\approx P(A)P(B)$. Here these values are {p['P_A_and_B']['value']:.4f} and {p['P_A_times_P_B']:.4f}; also $P(A\mid B)={p['P_A_given_B']['value']:.4f}$ versus $P(A)={p['P_A']['value']:.4f}$. This is an exploratory comparison of frequencies on the same subset, not a formal independence test.
\section{{Bernoulli variable and hypothetical binomial count}}
Let $X(r)=1\{{A(r)=1\}}$. Its empirical PMF is $P(X=0)={1-p['P_A']['value']:.4f}$ and $P(X=1)=p_A={p['P_A']['value']:.4f}$. Treating the observed cohort distribution as the empirical distribution, $E[X]=p={p['P_A']['value']:.4f}$ and $\operatorname{{Var}}(X)=p(1-p)={p['P_A']['value']*(1-p['P_A']['value']):.4f}$ (divisor-$n$ distribution variance). Table~\ref{{tab:pmf}} tabulates its counts and masses.
\begin{{table}}[H]\centering\caption{{Empirical Bernoulli probability mass function}}\label{{tab:pmf}}\begin{{tabular}}{{lrr}}\toprule Outcome & Count & Probability\\\midrule No MCI/dementia & {c['marginal_not_A']} & {1-p['P_A']['value']:.4f}\\ MCI or dementia & {c['marginal_A']} & {p['P_A']['value']:.4f}\\\bottomrule\end{{tabular}}\end{{table}}
For a fixed hypothetical $n=10$, define $Y=\sum_{{i=1}}^{{10}}X_i$ for independent Bernoulli draws with the same $p={p['P_A']['value']:.4f}$. Then $Y\sim\operatorname{{Binomial}}(10,p)$, $E[Y]=np={10*p['P_A']['value']:.3f}$ and $\operatorname{{Var}}(Y)=np(1-p)={10*p['P_A']['value']*(1-p['P_A']['value']):.3f}$. This model requires fixed trial count, independence, two outcomes, and constant success probability. It represents hypothetical independent draws; sampling distinct participants without replacement from this finite cohort is not exactly binomial. Estimating $p$ from this subset does not establish population-wide risk. Figure~\ref{{fig:binom}} plots the PMF. Repeated visits are not treated as independent trials.
\section{{Continuous distributions and normal approximation}}
MoCA is a bounded, discrete score (0--30), not literally continuous. For valid $n={d['MOCATOTS_points']['n']}$, mean={d['MOCATOTS_points']['mean']:.3f}, empirical variance (divisor $n$)={d['MOCATOTS_points']['variance_population_divisor_n']:.3f} points$^2$, median={d['MOCATOTS_points']['median']:.2f}; moment skewness={d['MOCATOTS_points']['skewness_moment']:.3f}. The 1.5$\times$IQR fences are [{d['MOCATOTS_points']['fence_low']:.2f}, {d['MOCATOTS_points']['fence_high']:.2f}] with {d['MOCATOTS_points']['outliers_1_5_iqr']} observations outside. Its negative skew, score bounds, and accumulation toward the upper end are visible in the plots and make a normal approximation unsuitable near the ceiling and tails.
Bilateral entorhinal volume is positive quantitative MRI data in mm$^3$. For valid $n={d['bilateral_entorhinal_volume_mm3']['n']}$, mean={d['bilateral_entorhinal_volume_mm3']['mean']:.2f}, empirical variance (divisor $n$)={d['bilateral_entorhinal_volume_mm3']['variance_population_divisor_n']:.2f} (mm$^3$)$^2$, median={d['bilateral_entorhinal_volume_mm3']['median']:.2f}; moment skewness={d['bilateral_entorhinal_volume_mm3']['skewness_moment']:.3f}. The 1.5$\times$IQR fences are [{d['bilateral_entorhinal_volume_mm3']['fence_low']:.2f}, {d['bilateral_entorhinal_volume_mm3']['fence_high']:.2f}] mm$^3$, with {d['bilateral_entorhinal_volume_mm3']['outliers_1_5_iqr']} observations outside. Histograms and Q--Q plots (Figures~\ref{{fig:moca}}--\ref{{fig:vqq}}) show moderate positive skew and high-tail departures from normality. Outliers remain included; a normal approximation may describe central shape but is less suitable in tails.
\begin{{figure}}[H]\centering\includegraphics[width=.9\linewidth]{{figures/phase2/group_probabilities.pdf}}\caption{{MCI or dementia probability by median-defined volume group; counts and group denominators shown.}}\label{{fig:group}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=.88\linewidth]{{figures/phase2/binomial_pmf.pdf}}\caption{{Hypothetical $\operatorname{{Binomial}}(10,p)$ probability mass function.}}\label{{fig:binom}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=.85\linewidth]{{figures/phase2/moca_histogram.pdf}}\caption{{Valid MOCATOTS histogram and fitted normal density overlay.}}\label{{fig:moca}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=.85\linewidth]{{figures/phase2/volume_histogram.pdf}}\caption{{Valid bilateral volume histogram and fitted normal density overlay.}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=.85\linewidth]{{figures/phase2/moca_qq.pdf}}\caption{{MoCA normal Q--Q plot.}}\end{{figure}}
\begin{{figure}}[H]\centering\includegraphics[width=.85\linewidth]{{figures/phase2/volume_qq.pdf}}\caption{{Bilateral volume normal Q--Q plot.}}\label{{fig:vqq}}\end{{figure}}
\section{{MoCA and MRI covariance}}
For {a['n']} pairwise-complete age-eligible participants, sample covariance using denominator $n-1$ is {a['sample_covariance_MoCA_points_times_mm3']:.4f} score-points$\cdot$mm$^3$, and Pearson correlation is $r={a['Pearson_r']:.4f}$. The direction is positive and magnitude describes a modest linear association in this subset. Correlation measures linear association only and does not establish causation. Figure~\ref{{fig:scatter}} labels both measurements and displays the paired cases.
\begin{{figure}}[H]\centering\includegraphics[width=.9\linewidth]{{figures/phase2/moca_volume_scatter.pdf}}\caption{{Pairwise-complete MoCA and bilateral entorhinal volume observations; descriptive fitted line.}}\label{{fig:scatter}}\end{{figure}}
\section{{Bayes' theorem}}
From the same table, $P(B\mid A)=n_{{11}}/n_A={c['rows'][0]['count']}/{c['marginal_A']}={p['P_B_given_A']['value']:.6f}$. Bayes' theorem gives $P(A\mid B)P(B)/P(A)=({p['P_A_given_B']['value']:.6f})({p['P_B']['value']:.6f})/({p['P_A']['value']:.6f})={p['bayes_rhs']:.6f}$. The computed sides differ by {p['bayes_identity_absolute_difference']:.2g}. This updates an event probability within this dataset-defined event system; it is not validated individual diagnostic prediction.
\section{{Limitations and conclusion}}
This is a descriptive analysis of a supplied clinical/research subset, not a population-representative sample. The files cannot verify baseline status, visit timing, or UDS--MRI contemporaneity. UDS values are processed/imputed; the original missingness mask and imputation method are unavailable. The median split is a descriptive partition, and empirical probabilities are not causal or clinical predictions. Normal plots are visual assessments; no observations were removed under the outlier rule. The data show differing empirical frequencies across volume groups and a positive descriptive linear association between MoCA and volume, subject to these design limits.
\section*{{Reproducibility and data definitions}}
Run \texttt{{python3 src/phase2\_analysis.py}} (or the bundled GapGPT Python runtime command documented in README) from the repository root. Results and audit tables are in \texttt{{reports/phase2/}}, figures in \texttt{{figures/phase2/}}. The original participant-level CSVs are not copied into generated reports. Phase 1 files remain separate.
\begin{{thebibliography}}{{9}}\bibitem{{data}}National Alzheimer’s Coordinating Center. Prepared course-subset CSVs: \texttt{{udslong\_imputed.csv}} and \texttt{{mriscanclean.csv}}. Data dictionary and preprocessing details were not supplied with this repository.\end{{thebibliography}}
\end{{document}}
'''
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
    P("Phase 2: Descriptive Probability Analysis of MoCA and Entorhinal Volume","Title")
    P("Research question: Among linked participants aged 65 years or older, how do empirical probabilities of MCI or dementia vary across bilateral entorhinal-volume groups, and what are the distributions and linear association of MoCA and volume?")
    section("Data, continuity, and analytic flow")
    P("The participant key is NACCID. The supplied records are retained one per unique participant after uniqueness checks. The age restriction is NACCAGE ≥ 65, matching Phase 1. MOCATOTS values outside [0,30] are invalid; valid fractional scores are retained. EDUC=99 is unknown. Bilateral volume is the mean of positive left and right entorhinal volumes.")
    P("The data lack visit IDs/dates and MRI scan dates, so the supplied row cannot be confirmed as baseline and UDS/MRI contemporaneity cannot be established. The UDS file is processed/imputed; the method and original missingness mask are unavailable. The subset is not representative of all older adults.")
    table([["Stage","n"]]+[[q["step"],str(q["n"])] for q in r["flow"]],[5.2*inch,1.1*inch])
    section("Events and joint probabilities")
    p=r["probabilities"];c=r["contingency"]
    P(f"A=1 when NACCUDSD is 3 (MCI) or 4 (dementia), a dataset-coded classification and not a new clinical diagnosis. B=1 when bilateral volume is at or below the age-eligible median, {r['events']['volume_median_n']} valid observations with a median of {r['events']['median_mm3']:.1f} mm³. Linear interpolation defines the median; {r['events']['equal_to_median_n']} tied value(s) are assigned to B=1. The common valid 2×2 denominator is {c['denominator']}.")
    table([["","B=1","B=0","Total"],["A=1",str(c["rows"][0]["count"]),str(c["rows"][1]["count"]),str(c["marginal_A"])],["A=0",str(c["rows"][2]["count"]),str(c["rows"][3]["count"]),str(c["marginal_not_A"])],["Total",str(c["marginal_B"]),str(c["marginal_not_B"]),str(c["denominator"])]])
    story.append(PageBreak())
    P(f"P(A)={p['P_A']['numerator']}/{p['P_A']['denominator']}={p['P_A']['value']:.4f}; P(B)={p['P_B']['numerator']}/{p['P_B']['denominator']}={p['P_B']['value']:.4f}; P(A∩B)={p['P_A_and_B']['numerator']}/{p['P_A_and_B']['denominator']}={p['P_A_and_B']['value']:.4f}. P(A|B)={p['P_A_given_B']['numerator']}/{p['P_A_given_B']['denominator']}={p['P_A_given_B']['value']:.4f}; P(A|not B)={p['P_A_given_not_B']['numerator']}/{p['P_A_given_not_B']['denominator']}={p['P_A_given_not_B']['value']:.4f}. These are empirical contrasts, not causal effects.")
    section("Group comparison and independence")
    P(f"In the lower-volume group, A occurs {r['groups'][0]['n_MCI_or_dementia']}/{r['groups'][0]['n_group']}={r['groups'][0]['percent']:.1f}%; above the median it occurs {r['groups'][1]['n_MCI_or_dementia']}/{r['groups'][1]['n_group']}={r['groups'][1]['percent']:.1f}%. The six age-eligible code-2 observations form a small original status category.")
    story.append(Image(str(FIG/"group_probabilities.png"),width=440,height=254));story.append(Spacer(1,8))
    P(f"P(A∩B)={p['P_A_and_B']['value']:.4f} and P(A)P(B)={p['P_A_times_P_B']:.4f}; P(A|B)={p['P_A_given_B']['value']:.4f} differs from P(A)={p['P_A']['value']:.4f}. This is an exploratory same-subset frequency comparison, not a formal test.")
    section("Bernoulli and binomial model")
    P(f"X=1{{A}} has empirical PMF P(X=0)={1-p['P_A']['value']:.4f}, P(X=1)={p['P_A']['value']:.4f}. E[X]={p['P_A']['value']:.4f} and empirical distribution Var(X)=p(1-p)={p['P_A']['value']*(1-p['P_A']['value']):.4f} with divisor n. For hypothetical n=10 independent draws, Y~Binomial(10,p), E[Y]={r['binomial']['expected']:.3f} and Var(Y)={r['binomial']['variance']:.3f}. This requires fixed n, independent trials, constant p, and two outcomes; distinct finite-cohort draws without replacement are not exactly binomial. No repeated visits are treated as trials.")
    table([["x","Outcome","Count","Empirical probability"]]+[[str(z["x"]),z["label"],str(z["count"]),f"{z['probability']:.4f}"] for z in r["bernoulli"]["pmf"]])
    story.append(Image(str(FIG/"binomial_pmf.png"),width=440,height=254));story.append(Spacer(1,8))
    section("Continuous measures and normal approximation")
    for name,s,unit in [("MOCATOTS",r["continuous"]["MOCATOTS_points"],"score points"),("Bilateral entorhinal volume",r["continuous"]["bilateral_entorhinal_volume_mm3"],"mm³")]:
        shape="MoCA's distribution is left-skewed with concentration near its upper bound, so a normal approximation is poor near the ceiling and in the tails." if name=="MOCATOTS" else "Volume is mildly right-skewed with a longer upper tail; the central histogram is closer to bell-shaped than its extremes, so a normal approximation is only a rough central summary."
        P(f"{name}: n={s['n']}, mean={s['mean']:.3f}, empirical variance (divisor n)={s['variance_population_divisor_n']:.3f}, median={s['median']:.3f}, moment skewness={s['skewness_moment']:.3f}, 1.5×IQR fences=[{s['fence_low']:.3f}, {s['fence_high']:.3f}] {unit}, outliers outside fences={s['outliers_1_5_iqr']}. All values are retained. {shape}","Small")
    for stem in ("moca","volume"):
        story.append(Image(str(FIG/(stem+"_histogram.png")),width=420,height=260));story.append(Spacer(1,5))
        story.append(Image(str(FIG/(stem+"_qq.png")),width=420,height=260));story.append(Spacer(1,7))
    section("MoCA and volume covariance")
    P(f"For n={r['association']['n']} pairwise-complete participants, sample covariance (n−1 denominator)={r['association']['sample_covariance_MoCA_points_times_mm3']:.4f} score-points·mm³ and Pearson r={r['association']['Pearson_r']:.4f}. The positive association describes linear co-variation, not causation.")
    story.append(Image(str(FIG/"moca_volume_scatter.png"),width=440,height=274))
    story.append(PageBreak());section("Bayes identity, limitations, and conclusion")
    P(f"Starting from marginal P(B), observing A updates it to P(B|A)={c['rows'][0]['count']}/{c['marginal_A']}={p['P_B_given_A']['value']:.6f}. Bayes gives P(A|B)P(B)/P(A)={p['P_A_given_B']['value']:.6f}×{p['P_B']['value']:.6f}/{p['P_A']['value']:.6f}={p['bayes_rhs']:.6f}; absolute difference={p['bayes_identity_absolute_difference']:.2g}. This is a dataset event calculation, not validated diagnostic prediction.")
    P("The available files cannot establish baseline status or temporal alignment. Original missingness and imputation details are unavailable. Probabilities apply only to the supplied eligible clinical/research subset. No significance tests, confidence intervals, or causal estimates are used.")
    P("Data definitions follow the supplied project data guide and column conventions in data/README.md; original NACC/SCAN codebooks and the assignment PDF were not included in the repository.","Small")
    P("Reproduce with python3 src/phase2_analysis.py using the documented runtime. Auditable JSON and CSV tables are in reports/phase2; figures are in figures/phase2.","Small")
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
