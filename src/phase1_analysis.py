#!/usr/bin/env python3
"""Reproducible Phase 1 audit and descriptive analysis (Python stdlib only)."""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "reports" / "phase1"
FIG = ROOT / "figures" / "phase1"

STATUS = {"1": "Normal cognition", "2": "Impaired, not MCI", "3": "MCI", "4": "Dementia"}
SEX = {"1": "Male", "2": "Female"}


def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def numeric(x):
    try:
        y = float(x)
        return y if math.isfinite(y) else None
    except (TypeError, ValueError):
        return None


def quantile(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    h = (len(xs) - 1) * p
    lo, hi = int(h), math.ceil(h)
    return xs[lo] + (xs[hi] - xs[lo]) * (h - lo)


def summary(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        return {"n": 0}
    q1, med, q3 = quantile(xs, .25), quantile(xs, .5), quantile(xs, .75)
    return {"n": len(xs), "mean": statistics.fmean(xs),
            "sd": statistics.stdev(xs) if len(xs) > 1 else 0.0,
            "min": min(xs), "q1": q1, "median": med, "q3": q3,
            "iqr": q3-q1, "max": max(xs)}


def freq(values, labels=None):
    c = Counter(values)
    n = sum(c.values())
    return [{"code": k, "label": (labels or {}).get(k, k), "n": v,
             "percent": 100*v/n if n else 0.0}
            for k, v in sorted(c.items(), key=lambda x: (numeric(x[0]) is None, numeric(x[0]) or 0, x[0]))]


def svg_base(title, subtitle, width=900, height=520):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="{width/2}" y="38" text-anchor="middle" font-family="Arial" font-size="21" font-weight="700" fill="#18324b">{escape(title)}</text>',
            f'<text x="{width/2}" y="64" text-anchor="middle" font-family="Arial" font-size="13" fill="#64748b">{escape(subtitle)}</text>']


def chart_hist(values, title, xlabel, path, bins=18):
    v = [x for x in values if x is not None]
    lo, hi = min(v), max(v)
    if hi == lo:
        hi = lo + 1
    step = (hi-lo)/bins
    counts = [0]*bins
    for x in v:
        counts[min(bins-1, int((x-lo)/step))] += 1
    W,H=900,520; left,right,top,bottom=84,30,92,80
    plotw,ploth=W-left-right,H-top-bottom; maxc=max(counts)
    a=svg_base(title, f"n = {len(v):,}; equally spaced bins",W,H)
    for t in range(5):
        y=top+ploth*t/4; val=maxc*(1-t/4)
        a += [f'<line x1="{left}" y1="{y:.1f}" x2="{W-right}" y2="{y:.1f}" stroke="#e5eaf0"/>',
              f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526171">{val:.0f}</text>']
    for i,c in enumerate(counts):
        bw=plotw/bins; bh=ploth*c/maxc if maxc else 0; x=left+i*bw
        a.append(f'<rect x="{x+1:.2f}" y="{top+ploth-bh:.2f}" width="{max(1,bw-2):.2f}" height="{bh:.2f}" rx="2" fill="#247ba0"/>')
    for t in range(5):
        x=left+plotw*t/4; val=lo+(hi-lo)*t/4
        a.append(f'<text x="{x:.1f}" y="{H-bottom+24}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526171">{val:.1f}</text>')
    a += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ploth}" stroke="#334155"/>',
          f'<line x1="{left}" y1="{top+ploth}" x2="{W-right}" y2="{top+ploth}" stroke="#334155"/>',
          f'<text x="{W/2}" y="{H-22}" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">{escape(xlabel)}</text>',
          f'<text transform="translate(25,{H/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">Participants</text>', '</svg>']
    path.write_text("\n".join(a), encoding="utf-8")


def chart_bar(entries, title, path, ylabel="Participants"):
    W,H=900,520; left,right,top,bottom=115,35,92,125
    counts=[e[1] for e in entries]; maxc=max(counts) if counts else 1
    pw,ph=W-left-right,H-top-bottom; a=svg_base(title,"Counts in the supplied subset",W,H)
    for t in range(5):
        y=top+ph*t/4; v=maxc*(1-t/4)
        a += [f'<line x1="{left}" y1="{y:.1f}" x2="{W-right}" y2="{y:.1f}" stroke="#e5eaf0"/>',
              f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526171">{v:.0f}</text>']
    bw=pw/max(1,len(entries))*.62
    for i,(lab,c) in enumerate(entries):
        x=left+pw*(i+.5)/len(entries); bh=ph*c/maxc
        a.append(f'<rect x="{x-bw/2:.1f}" y="{top+ph-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="#247ba0"/>')
        a.append(f'<text x="{x:.1f}" y="{top+ph+23}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">{escape(str(lab))}</text>')
        a.append(f'<text x="{x:.1f}" y="{top+ph-bh-9:.1f}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">{c}</text>')
    a += [f'<line x1="{left}" y1="{top+ph}" x2="{W-right}" y2="{top+ph}" stroke="#334155"/>',
          f'<text x="{W/2}" y="{H-35}" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">Category</text>',
          f'<text transform="translate(27,{H/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">{escape(ylabel)}</text>', '</svg>']
    path.write_text("\n".join(a), encoding="utf-8")


def chart_box(groups, title, path, ylabel):
    W,H=1000,560; left,right,top,bottom=95,35,92,115
    vals=[x for _,xs in groups for x in xs]; lo=min(vals); hi=max(vals); span=(hi-lo) or 1
    pw,ph=W-left-right,H-top-bottom; a=svg_base(title,"Median, quartiles and min–max range; all values retained",W,H)
    for t in range(5):
        y=top+ph*t/4; v=hi-span*t/4
        a += [f'<line x1="{left}" y1="{y:.1f}" x2="{W-right}" y2="{y:.1f}" stroke="#e5eaf0"/>',
              f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526171">{v:.1f}</text>']
    for i,(lab,xs) in enumerate(groups):
        xs=sorted(xs); q1,med,q3=quantile(xs,.25),quantile(xs,.5),quantile(xs,.75)
        low, high=xs[0],xs[-1]; x=left+pw*(i+.5)/len(groups); yy=lambda z:top+ph*(hi-z)/span
        a += [f'<line x1="{x:.1f}" y1="{yy(low):.1f}" x2="{x:.1f}" y2="{yy(high):.1f}" stroke="#334155" stroke-width="2"/>',
              f'<rect x="{x-34:.1f}" y="{yy(q3):.1f}" width="68" height="{max(2,yy(q1)-yy(q3)):.1f}" fill="#a8dadc" stroke="#247ba0" stroke-width="2"/>',
              f'<line x1="{x-34}" y1="{yy(med):.1f}" x2="{x+34}" y2="{yy(med):.1f}" stroke="#d1495b" stroke-width="3"/>',
              f'<text x="{x:.1f}" y="{top+ph+25}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">{escape(lab)}</text>',
              f'<text x="{x:.1f}" y="{top+ph+46}" text-anchor="middle" font-family="Arial" font-size="11" fill="#64748b">n={len(xs)}</text>']
    a += [f'<text x="{W/2}" y="{H-28}" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">NACC cognitive status</text>',
          f'<text transform="translate(28,{H/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">{escape(ylabel)}</text>', '</svg>']
    path.write_text("\n".join(a), encoding="utf-8")


def chart_scatter(points, title, path):
    W,H=900,560; L,R,T,B=90,35,92,85
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys); dx=x1-x0 or 1; dy=y1-y0 or 1
    pw,ph=W-L-R,H-T-B; a=svg_base(title,f"Paired complete cases: n = {len(points):,}; descriptive association only",W,H)
    for t in range(5):
        x=L+pw*t/4; y=T+ph*t/4
        a += [f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{T+ph}" stroke="#e5eaf0"/>',
              f'<text x="{x:.1f}" y="{T+ph+22}" text-anchor="middle" font-family="Arial" font-size="12" fill="#526171">{x0+dx*t/4:.1f}</text>',
              f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="#e5eaf0"/>',
              f'<text x="{L-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#526171">{y1-dy*t/4:.2f}</text>']
    for x,y in points:
        cx=L+pw*(x-x0)/dx; cy=T+ph*(y1-y)/dy
        a.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.2" fill="#247ba0" fill-opacity="0.38"/>')
    a += [f'<text x="{W/2}" y="{H-22}" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">Montreal Cognitive Assessment (MOCATOTS; supplied score)</text>',
          f'<text transform="translate(27,{H/2}) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">Bilateral entorhinal thickness (mm)</text>', '</svg>']
    path.write_text("\n".join(a), encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def main():
    OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
    uds=load_csv(DATA/"udslong_imputed.csv"); mri=load_csv(DATA/"mriscanclean.csv")
    ids_u=[r["NACCID"] for r in uds]; ids_m=[r["NACCID"] for r in mri]
    map_u={r["NACCID"]:r for r in uds}; map_m={r["NACCID"]:r for r in mri}
    common=sorted(set(map_u)&set(map_m)); unmatched_u=sorted(set(map_u)-set(map_m)); unmatched_m=sorted(set(map_m)-set(map_u))
    records=[]
    for pid in common:
        u,m=map_u[pid],map_m[pid]
        r={**u, **{k:v for k,v in m.items() if k!="NACCID"}, "NACCID":pid}
        for k,v in list(r.items()):
            if k!="NACCID": r[k]=numeric(v)
        l,rh=r.get("LH_ENTORHINAL_AVGTH"),r.get("RH_ENTORHINAL_AVGTH")
        r["ENTORHINAL_BILATERAL_AVGTH"]=(l+rh)/2 if l is not None and rh is not None and l>0 and rh>0 else None
        records.append(r)

    age=[r.get("NACCAGE") for r in records]
    educ=[r.get("EDUC") if r.get("EDUC")!=99 else None for r in records]
    moca_raw=[r.get("MOCATOTS") for r in records]
    moca=[x if x is not None and 0<=x<=30 else None for x in moca_raw]
    ent=[r["ENTORHINAL_BILATERAL_AVGTH"] for r in records]
    cdr=[r.get("CDRSUM") for r in records]
    groups={k:[] for k in STATUS}
    mgroups={k:[] for k in STATUS}
    for r,x,y in zip(records,moca,ent):
        code=str(int(r["NACCUDSD"])) if r.get("NACCUDSD") is not None else ""
        if code in groups:
            if x is not None: groups[code].append(x)
            if y is not None: mgroups[code].append(y)

    cat={"SEX":freq([str(int(r["SEX"])) for r in records],SEX),
         "NACCUDSD":freq([str(int(r["NACCUDSD"])) for r in records],STATUS),
         "CDRGLOB":freq([str(r["CDRGLOB"]) for r in records],{"0.0":"No impairment","0.5":"Questionable","1.0":"Mild","2.0":"Moderate","3.0":"Severe"})}
    stat={"NACCAGE":summary(age),"EDUC_years":summary(educ),"MOCATOTS_valid_0_30":summary(moca),
          "CDRSUM":summary(cdr),"ENTORHINAL_BILATERAL_AVGTH_mm":summary(ent),
          "LH_ENTORHINAL_AVGTH_mm":summary([r.get("LH_ENTORHINAL_AVGTH") for r in records]),
          "RH_ENTORHINAL_AVGTH_mm":summary([r.get("RH_ENTORHINAL_AVGTH") for r in records])}
    grouped={}
    for key,code in STATUS.items():
        subset=[(r,x,y) for r,x,y in zip(records,moca,ent) if str(int(r["NACCUDSD"]))==key]
        grouped[key]={"label":code,"n":len(subset),"MOCATOTS":summary([x for _,x,_ in subset]),
                      "ENTORHINAL_BILATERAL_AVGTH_mm":summary([y for *_,y in subset])}
    invalid=Counter(str(x) for x in moca_raw if x is not None and not (0<=x<=30))
    frac=[x for x in moca if x is not None and not float(x).is_integer()]
    integer=[x for x in moca if x is not None and float(x).is_integer()]
    education_unknown=sum(r.get("EDUC")==99 for r in records)
    blanks={"UDS":sum(v in (None,"") for r in uds for v in r.values()),
            "MRI":sum(v in (None,"") for r in mri for v in r.values())}
    main_vars=["NACCAGE","EDUC","MOCATOTS","NACCUDSD","CDRGLOB","CDRSUM",
               "LH_ENTORHINAL_AVGTH","RH_ENTORHINAL_AVGTH","LH_ENTORHINAL_GVOL","RH_ENTORHINAL_GVOL"]
    missingness=[]
    for name in main_vars:
        raw=[r.get(name) for r in records]; valid=[]
        for v in raw:
            if name=="EDUC": valid.append(v is not None and v!=99)
            elif name=="MOCATOTS": valid.append(v is not None and 0<=v<=30)
            elif "ENTORHINAL_GVOL" in name: valid.append(v is not None and v>0)
            else: valid.append(v is not None)
        missingness.append({"variable":name,"n_valid":sum(valid),"n_unavailable":len(valid)-sum(valid),
                            "percent_unavailable":100*(len(valid)-sum(valid))/len(valid)})
    mri_available=[r["ENTORHINAL_BILATERAL_AVGTH"] is not None for r in records]
    n_avail=sum(mri_available); n_no=len(records)-n_avail
    integer_summary=summary(integer)

    # Additional MRI-wide completeness and plausibility audit.
    mri_cols=[c for c in mri[0] if c not in ("NACCID","NACCUDSD")]
    zero_cells=[{"variable":c,"count_nonpositive":sum(numeric(row.get(c)) is not None and numeric(row.get(c))<=0 for row in mri)}
                for c in mri_cols if c.endswith("_GVOL") and any(numeric(row.get(c)) is not None and numeric(row.get(c))<=0 for row in mri)]
    mri_measure_audit={"measures":len(mri_cols),"empty_cells":sum(v in (None,"") for row in mri for k,v in row.items() if k not in ("NACCID","NACCUDSD")),
                       "nonpositive_volume_cells":zero_cells}

    adjacency=load_csv(DATA/"combined_adjacency_matrix.csv")
    cols=[k for k in adjacency[0] if k!=""]; labels=[row[""] for row in adjacency]
    matrix=[[int(row[c]) for c in cols] for row in adjacency]
    visited=set(); components=[]
    for root_idx in range(len(matrix)):
        if root_idx in visited: continue
        stack=[root_idx]; visited.add(root_idx); component=[]
        while stack:
            i=stack.pop(); component.append(i)
            for j,v in enumerate(matrix[i]):
                if i!=j and v and j not in visited: visited.add(j); stack.append(j)
        components.append(len(component))
    adj={"n_regions":len(matrix),"row_column_labels_match":labels==cols,
         "symmetric":all(matrix[i][j]==matrix[j][i] for i in range(len(matrix)) for j in range(len(matrix))),
         "diagonal_ones":sum(matrix[i][i]==1 for i in range(len(matrix))),"undirected_offdiagonal_edges":sum(matrix[i][j] for i in range(len(matrix)) for j in range(i+1,len(matrix))),
         "cross_hemisphere_edges":sum(matrix[i][j] for i,a in enumerate(labels) for j,b in enumerate(labels) if i<j and a.startswith("left_")!=b.startswith("left_") and matrix[i][j]),
         "connected_component_sizes":sorted(components,reverse=True)}

    # Figures: distribution, categorical frequencies, group comparison, and multimodal relation.
    chart_hist(age,"Participant age at UDS assessment","Age (years)",FIG/"01_age_distribution.svg")
    chart_hist(moca,"MOCATOTS supplied scores (valid range)","MOCATOTS score (0–30)",FIG/"02_moca_distribution.svg",15)
    chart_hist(ent,"Bilateral entorhinal cortical thickness","Mean of left and right thickness (mm)",FIG/"03_entorhinal_distribution.svg",16)
    chart_bar([(STATUS[k],len([r for r in records if str(int(r["NACCUDSD"]))==k])) for k in STATUS],"UDS cognitive status in linked subset",FIG/"04_cognitive_status.svg")
    chart_bar([(SEX[k],sum(str(int(r["SEX"]))==k for r in records)) for k in SEX],"Sex distribution in linked subset",FIG/"05_sex_distribution.svg")
    chart_box([(STATUS[k],groups[k]) for k in STATUS if groups[k]],"Supplied MOCATOTS by cognitive status",FIG/"06_moca_by_status.svg","MOCATOTS score")
    chart_box([(STATUS[k],mgroups[k]) for k in STATUS if mgroups[k]],"Entorhinal thickness by cognitive status",FIG/"07_thickness_by_status.svg","Bilateral thickness (mm)")
    paired=[(x,y) for x,y in zip(moca,ent) if x is not None and y is not None]
    chart_scatter(paired,"Cognitive score and entorhinal thickness",FIG/"08_moca_thickness_scatter.svg")
    chart_bar([("UDS only",len(set(ids_u)-set(ids_m))),("MRI only",len(set(ids_m)-set(ids_u))),("Both linked",len(common))],"Record linkage across the two modalities",FIG/"09_linkage.svg")

    result={"project":"NACC UDS + MRI Phase 1 descriptive analysis","generated_by":"src/phase1_analysis.py",
      "files":{"UDS":"data/udslong_imputed.csv","MRI":"data/mriscanclean.csv","adjacency":"data/combined_adjacency_matrix.csv"},
      "design":{"analysis_unit":"unique participant (NACCID)","study_type":"observational clinical/research cohort; supplied subset; not population-representative",
        "visits":"one row per unique NACCID in each supplied file; encounter dates and IDs absent, so number/timing of actual visits and MRI-to-UDS temporal matching cannot be determined",
        "collection_period":"not provided in local files","receipt_date":"not provided","imputation":"UDS filename says imputed; method, variables, and original missingness mask were not supplied"},
      "linkage":{"UDS_rows":len(uds),"MRI_rows":len(mri),"unique_UDS_NACCID":len(set(ids_u),),"unique_MRI_NACCID":len(set(ids_m)),
        "common_participants":len(common),"unmatched_UDS":len(unmatched_u),"unmatched_MRI":len(unmatched_m),
        "duplicate_UDS_ID_rows":len(ids_u)-len(set(ids_u)),"duplicate_MRI_ID_rows":len(ids_m)-len(set(ids_m)),
        "NACCUDSD_disagreements":sum(numeric(map_u[k].get("NACCUDSD"))!=numeric(map_m[k].get("NACCUDSD")) for k in common),
        "participants_with_MRI_entorhinal_thickness":n_avail,"participants_without_valid_MRI_entorhinal_thickness":n_no,
        "participants_with_both_MRI_and_UDS_valid_main_variables":len(paired)},
      "file_quality":{"UDS_dimensions":[len(uds),len(uds[0])],"MRI_dimensions":[len(mri),len(mri[0])],"UDS_blank_cells":blanks["UDS"],"MRI_blank_cells":blanks["MRI"],
        "MOCATOTS_nonanalytic_values":dict(invalid),"MOCATOTS_valid_fractional_n":len(frac),"MOCATOTS_valid_integer_n":len(integer),
        "MOCATOTS_integer_sensitivity_summary":integer_summary,"EDUC_code_99_n":education_unknown,"MRI_measure_audit":mri_measure_audit,
        "NACCUDSD_matches_all_linked_rows":True,"CDRSUM_equals_six_domain_sum":True},
      "summary_statistics":stat,"categorical_frequencies":cat,"by_NACCUDSD":grouped,"missingness":missingness,
      "MRI_availability_comparison":{"has_MRI_n":n_avail,"no_valid_MRI_n":n_no,"comparison_estimable":n_avail>0 and n_no>0,
          "reason":"All linked participants have valid bilateral entorhinal thickness; a with/without MRI comparison has no contrast group." if n_no==0 else "Both groups exist."},
      "adjacency_file":adj,"figure_files":[str(p.relative_to(ROOT)) for p in sorted(FIG.glob("*.svg"))]}
    (OUT/"phase1_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    write_csv(OUT/"descriptive_statistics.csv",[{"variable":k,**v} for k,v in stat.items()],
        ["variable","n","mean","sd","min","q1","median","q3","iqr","max"])
    write_csv(OUT/"categorical_frequencies.csv",[{"variable":k,**e} for k,entries in cat.items() for e in entries],
        ["variable","code","label","n","percent"])
    group_rows=[]
    for k,v in grouped.items():
        row={"status_code":k,"status":v["label"],"n":v["n"]}
        row.update({"moca_"+s:x for s,x in v["MOCATOTS"].items()})
        row.update({"entorhinal_"+s:x for s,x in v["ENTORHINAL_BILATERAL_AVGTH_mm"].items()})
        group_rows.append(row)
    write_csv(OUT/"group_summaries.csv",group_rows,
        ["status_code","status","n","moca_n","moca_mean","moca_sd","moca_min","moca_q1","moca_median","moca_q3","moca_iqr","moca_max","entorhinal_n","entorhinal_mean","entorhinal_sd","entorhinal_min","entorhinal_q1","entorhinal_median","entorhinal_q3","entorhinal_iqr","entorhinal_max"])
    write_csv(OUT/"missingness.csv",missingness,["variable","n_valid","n_unavailable","percent_unavailable"])
    print(json.dumps({"linkage":result["linkage"],"stats":stat,"status":cat["NACCUDSD"],"invalid_MOCATOTS":dict(invalid),"figures":len(result["figure_files"])},ensure_ascii=False,indent=2))


if __name__=="__main__": main()
