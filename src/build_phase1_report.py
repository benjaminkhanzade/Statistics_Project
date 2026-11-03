#!/usr/bin/env python3
"""Create the Persian Phase 1 PDF from the reproducible analysis outputs."""
import csv
import json
import math
import shutil
import statistics
import sys
from collections import Counter
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Flowable, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, KeepTogether)

SKILL = Path("/Users/benjamin/.gapcode/plugins/cache/gapgpt/pdf/26.722.10000/skills/pdf/scripts")
sys.path.insert(0, str(SKILL))
from fa_pdf import register_persian_fonts, rtl_line, rtl_paragraph, persian_digits

ROOT=Path(__file__).resolve().parents[1]
RESULT=ROOT/"reports/phase1/phase1_results.json"
FIG=ROOT/"figures/phase1"
PDF=ROOT/"reports/phase1/report_phase1.pdf"
OUT=ROOT/"reports/phase1"
ACC=colors.HexColor("#176B87"); INK=colors.HexColor("#1F2937"); MUTED=colors.HexColor("#64748B")
PALE=colors.HexColor("#EEF5F8"); GRID=colors.HexColor("#DCE5EB")

register_persian_fonts(ROOT/"src/assets/fonts")
data=json.loads(RESULT.read_text(encoding="utf-8"))


def fa_num(x, digits=2):
    if x is None: return "—"
    if isinstance(x,int) or (isinstance(x,float) and x.is_integer()): s=f"{int(x):,}"
    else: s=f"{x:,.{digits}f}"
    return persian_digits(s)


def fa_pct(x): return persian_digits(f"{x:.1f}٪")


styles=getSampleStyleSheet()
title=ParagraphStyle("faTitle",fontName="Vazirmatn-Bold",fontSize=25,leading=39,textColor=INK,alignment=TA_RIGHT,spaceAfter=6)
subtitle=ParagraphStyle("faSubtitle",fontName="Vazirmatn",fontSize=12,leading=22,textColor=MUTED,alignment=TA_RIGHT,spaceAfter=5)
h1=ParagraphStyle("faH1",fontName="Vazirmatn-Bold",fontSize=17,leading=29,textColor=ACC,alignment=TA_RIGHT,spaceBefore=9,spaceAfter=5)
h2=ParagraphStyle("faH2",fontName="Vazirmatn-Bold",fontSize=12,leading=22,textColor=INK,alignment=TA_RIGHT,spaceBefore=5,spaceAfter=3)
body=ParagraphStyle("faBody",fontName="Vazirmatn",fontSize=9.4,leading=18.5,textColor=INK,alignment=TA_RIGHT,spaceAfter=5)
small=ParagraphStyle("faSmall",fontName="Vazirmatn",fontSize=8.2,leading=15.5,textColor=INK,alignment=TA_RIGHT)
caption=ParagraphStyle("faCaption",fontName="Vazirmatn",fontSize=8.3,leading=16,textColor=MUTED,alignment=TA_RIGHT,spaceBefore=3,spaceAfter=8)
cell=ParagraphStyle("faCell",fontName="Vazirmatn",fontSize=7.7,leading=13,textColor=INK,alignment=TA_RIGHT)
headcell=ParagraphStyle("faHeadCell",fontName="Vazirmatn-Bold",fontSize=7.7,leading=13,textColor=colors.white,alignment=TA_RIGHT)

def p(text, style=body, width=None):
    return rtl_paragraph(text,style,width) if width else rtl_paragraph(text,style,170*mm)

def make_table(headers,rows,widths=None,font_style=cell):
    vals=[[rtl_line(str(h)) for h in headers]]
    vals += [[rtl_line(str(v)) for v in row] for row in rows]
    t=Table(vals,colWidths=widths,repeatRows=1,hAlign="RIGHT")
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),ACC),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Vazirmatn-Bold"),("FONTNAME",(0,1),(-1,-1),"Vazirmatn"),
        ("FONTSIZE",(0,0),(-1,-1),7.5),("LEADING",(0,0),(-1,-1),12),
        ("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("GRID",(0,0),(-1,-1),.35,GRID),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE])]))
    return t

def csvrows(name):
    with (ROOT/"data"/name).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
uds=csvrows("udslong_imputed.csv"); mri=csvrows("mriscanclean.csv")
mrimap={r["NACCID"]:r for r in mri}
def num(s):
    try:
        x=float(s)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError):return None
joined=[]
for u in uds:
    m=mrimap.get(u["NACCID"])
    if not m:continue
    x=num(u.get("MOCATOTS")); x=x if x is not None and 0<=x<=30 else None
    le,re=num(m.get("LH_ENTORHINAL_AVGTH")),num(m.get("RH_ENTORHINAL_AVGTH"))
    bt=(le+re)/2 if le is not None and re is not None and le>0 and re>0 else None
    joined.append({"age":num(u.get("NACCAGE")),"moca":x,"thickness":bt,
                   "status":int(float(u["NACCUDSD"])),"sex":int(float(u["SEX"]))})

class Figure(Flowable):
    def __init__(self,kind,width=164*mm,height=91*mm):
        Flowable.__init__(self);self.kind=kind;self.width=width;self.height=height
    def wrap(self,aW,aH):
        self.width=min(self.width,aW);return self.width,self.height
    def draw(self):
        c=self.canv;c.saveState();w,h=self.width,self.height
        L,R,T,B=22*mm,7*mm,9*mm,16*mm; pw=w-L-R; ph=h-T-B
        def axes(title_text,ylabel):
            c.setFillColor(INK);c.setFont("Helvetica-Bold",10);c.drawCentredString(w/2,h-4*mm,title_text)
            c.setStrokeColor(GRID);c.setLineWidth(.45)
            for i in range(5):
                y=B+ph*i/4;c.line(L,y,L+pw,y);c.setFillColor(MUTED);c.setFont("Helvetica",7);c.drawRightString(L-2*mm,y-2,ylabel[i] if isinstance(ylabel,list) else str(i))
            c.setStrokeColor(INK);c.line(L,B,L+pw,B);c.line(L,B,L,B+ph)
        if self.kind in ("age","moca","thickness"):
            if self.kind=="age": vals=[r["age"] for r in joined if r["age"] is not None]; title_text="Age at UDS assessment"; xlab="Age (years)"
            elif self.kind=="moca": vals=[r["moca"] for r in joined if r["moca"] is not None];title_text="Supplied MOCATOTS scores";xlab="MOCATOTS (valid range 0–30)"
            else: vals=[r["thickness"] for r in joined if r["thickness"] is not None];title_text="Bilateral entorhinal thickness";xlab="Mean left/right thickness (mm)"
            lo,hi=min(vals),max(vals);bins=18 if self.kind!="moca" else 15;step=(hi-lo)/bins or 1;counts=[0]*bins
            for v in vals:counts[min(bins-1,int((v-lo)/step))]+=1
            maxc=max(counts);axes(title_text,[f"{maxc*i/4:.0f}" for i in range(5)])
            bw=pw/bins
            c.setFillColor(ACC)
            for i,n in enumerate(counts):
                bh=ph*n/maxc;c.roundRect(L+i*bw+1,B,bw-2,bh,1.3,stroke=0,fill=1)
            c.setFillColor(MUTED);c.setFont("Helvetica",7)
            for i in range(5):c.drawCentredString(L+pw*i/4,B-4*mm,f"{lo+(hi-lo)*i/4:.1f}")
            c.setFillColor(INK);c.setFont("Helvetica",8);c.drawCentredString(w/2,2*mm,xlab)
        elif self.kind in ("status","sex"):
            if self.kind=="status": entries=[("Normal",847),("Impaired*",7),("MCI",252),("Dementia",131)];title_text="UDS cognitive status"
            else:entries=[("Male",497),("Female",740)];title_text="Sex distribution"
            maxc=max(x[1] for x in entries);axes(title_text,[f"{maxc*i/4:.0f}" for i in range(5)])
            bw=min(30*mm,pw/len(entries)*.56)
            for i,(lab,n) in enumerate(entries):
                x=L+pw*(i+.5)/len(entries);bh=ph*n/maxc;c.setFillColor(ACC);c.roundRect(x-bw/2,B,bw,bh,2,stroke=0,fill=1)
                c.setFillColor(INK);c.setFont("Helvetica",8);c.drawCentredString(x,B-4*mm,lab);c.drawCentredString(x,B+bh+2*mm,str(n))
        elif self.kind in ("moca_group","thick_group"):
            metric="moca" if self.kind=="moca_group" else "thickness";title_text="MOCATOTS by status" if metric=="moca" else "Entorhinal thickness by status"
            vals=[r[metric] for r in joined if r[metric] is not None];lo,hi=min(vals),max(vals);span=hi-lo or 1
            groups=[("Normal",1),("Impaired*",2),("MCI",3),("Dementia",4)];axes(title_text,[f"{lo+span*i/4:.1f}" for i in range(5)])
            for i,(lab,code) in enumerate(groups):
                arr=sorted(r[metric] for r in joined if r["status"]==code and r[metric] is not None)
                if not arr:continue
                n=len(arr)
                def q(z):
                    h=(n-1)*z; low=int(h); high=math.ceil(h)
                    return arr[low]+(arr[high]-arr[low])*(h-low)
                q1,med,q3=q(.25),q(.5),q(.75);x=L+pw*(i+.5)/len(groups); yy=lambda z:B+ph*(z-lo)/span
                c.setStrokeColor(INK);c.line(x,yy(arr[0]),x,yy(arr[-1]));c.setFillColor(colors.HexColor("#A8DADC"));c.setStrokeColor(ACC);c.rect(x-9*mm,yy(q1),18*mm,max(.8,yy(q3)-yy(q1)),stroke=1,fill=1)
                c.setStrokeColor(colors.HexColor("#D1495B"));c.setLineWidth(1.5);c.line(x-9*mm,yy(med),x+9*mm,yy(med));c.setFillColor(INK);c.setFont("Helvetica",7);c.drawCentredString(x,B-4*mm,lab);c.drawCentredString(x,B-8*mm,f"n={n}")
            c.setFillColor(INK);c.setFont("Helvetica",7);c.drawCentredString(w/2,2*mm,"Whiskers show min–max; very small group n=7")
        elif self.kind=="scatter":
            points=[(r["moca"],r["thickness"]) for r in joined if r["moca"] is not None and r["thickness"] is not None]
            xs=[a for a,b in points];ys=[b for a,b in points];x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);dx=x1-x0 or 1;dy=y1-y0 or 1
            axes("MOCATOTS and entorhinal thickness",[f"{y0+dy*i/4:.2f}" for i in range(5)])
            c.setFillColor(colors.Color(.09,.42,.53,alpha=.35))
            for x,y in points:c.circle(L+pw*(x-x0)/dx,B+ph*(y-y0)/dy,1.1,stroke=0,fill=1)
            c.setFillColor(INK);c.setFont("Helvetica",8);c.drawCentredString(w/2,2*mm,"Supplied MOCATOTS score (descriptive association)")
        elif self.kind=="linkage":
            entries=[("UDS only",0),("MRI only",0),("Both",1237)];maxc=1237;axes("One-to-one linkage by NACCID",[f"{maxc*i/4:.0f}" for i in range(5)])
            bw=min(28*mm,pw/len(entries)*.56)
            for i,(lab,n) in enumerate(entries):
                x=L+pw*(i+.5)/len(entries);bh=ph*n/maxc;c.setFillColor(ACC);c.roundRect(x-bw/2,B,bw,bh,2,stroke=0,fill=1);c.setFillColor(INK);c.setFont("Helvetica",8);c.drawCentredString(x,B-4*mm,lab);c.drawCentredString(x,B+bh+2*mm,str(n))
        c.restoreState()


def header_footer(c,doc):
    c.saveState();w,h=A4
    if doc.page>1:
        c.setStrokeColor(GRID);c.line(20*mm,h-15*mm,w-20*mm,h-15*mm)
        c.setFillColor(MUTED);c.setFont("Vazirmatn",7.5);c.drawRightString(w-20*mm,h-12*mm,rtl_line("پروژهٔ آمار | فاز اول | زیرمجموعهٔ NACC UDS + MRI"))
    c.setStrokeColor(GRID);c.line(20*mm,13*mm,w-20*mm,13*mm)
    c.setFillColor(MUTED);c.setFont("Vazirmatn",7.5);c.drawRightString(w-20*mm,8*mm,rtl_line("گزارش توصیفی؛ بدون آزمون استنباطی"))
    c.setFont("Helvetica",8);c.drawString(20*mm,8*mm,str(doc.page));c.restoreState()

story=[]
S=data["summary_statistics"]
L=data["linkage"]
story += [Spacer(1,15*mm),p("فاز اول: توصیف رابطهٔ MoCA و MRI انتورینال",title),p("جامعهٔ تحلیلی: سالمندان NACC؛ UDS + MRI",subtitle),Spacer(1,7*mm)]
story += [p("سؤال آماری",h1),p("در افراد ۶۵ ساله و بالاتر، نمرهٔ MOCATOTS چه رابطهٔ توصیفی با حجم و ضخامت قشر Entorhinal دارد؟ در فاز مدل‌سازی بعدی، سن NACCAGE و سال‌های تحصیلات EDUC به‌عنوان متغیرهای کنترل وارد خواهند شد.",body)]
story += [make_table(["مرحلهٔ نمونه","تعداد"],[["سطرهای UDS / افراد یکتای UDS",f"{L['UDS_rows']:,} / {L['unique_UDS_NACCID']:,}"],["سطرهای MRI / افراد یکتای MRI",f"{L['MRI_rows']:,} / {L['unique_MRI_NACCID']:,}"],["NACCID مشترک",f"{L['common_participants']:,}"],["افراد ۶۵ سال به بالا؛ نمونهٔ تحلیلی",f"{L['analytic_participants_age_65_plus']:,}"],["نمونهٔ کامل برای متغیرهای اصلی",f"{L['participants_with_both_MRI_and_UDS_valid_main_variables']:,}"]],[90*mm,73*mm]),Spacer(1,5*mm)]
story += [p("واحد تحلیل و قاعدهٔ انتخاب",h1),p("واحد تحلیل NACCID است. در هر دو فایل یک ردیف برای هر شناسه وجود دارد؛ تکرار شناسه دیده نشد. بنابراین همان ردیف یکتای موجود نگه داشته شد و سپس سن NACCAGE ≥ 65 شرط ورود به نمونهٔ سالمندان بود. فایل‌ها شناسه/تاریخ مراجعه و تاریخ MRI ندارند، پس نمی‌توان این ردیف را Baseline نامید یا هم‌زمانی UDS و MRI را احراز کرد.",body),p("آمار توصیفی نمونهٔ ۶۵+",h1)]
keys=[("NACCAGE","سن، سال"),("EDUC_years","تحصیلات، سال"),("MOCATOTS_valid_0_30","MOCATOTS"),("ENTORHINAL_BILATERAL_GVOL_mm3","حجم دوطرفه، mm³"),("ENTORHINAL_BILATERAL_AVGTH_mm","ضخامت دوطرفه، mm")]
rows=[]
for key,label in keys:
 s=S[key]; rows.append([label,fa_num(s['n'],0),fa_num(s['mean']),fa_num(s['median']),fa_num(s['sd']),fa_num(s['iqr']),fa_num(s['skewness'])])
story += [make_table(["متغیر","n","میانگین","میانه","SD","IQR","چولگی"],rows,[42*mm,15*mm,24*mm,22*mm,20*mm,20*mm,20*mm]),Spacer(1,4*mm),p("چولگی منفی MOCATOTS نشان می‌دهد نمره‌ها در این نمونه بیشتر در سمت بالای مقیاس متمرکزند. EDUC=99 نامعلوم تلقی شد؛ ۹ مقدار MOCATOTS خارج از دامنهٔ ۰–۳۰ حذف شد. حجم‌های نامثبت برای خلاصهٔ حجم قابل قبول نیستند. مقدارهای فایل UDS از دادهٔ جایگذاری‌شده‌اند و روش/نقاب مقادیر اولیه در دسترس نیست.",body),PageBreak()]
story += [p("گمشدگی و کیفیت",h1),make_table(["متغیر","معتبر n","نامعلوم/نامعتبر n","درصد"],[[r['variable'],fa_num(r['n_valid'],0),fa_num(r['n_unavailable'],0),fa_pct(r['percent_unavailable'])] for r in data['missingness']],[60*mm,30*mm,42*mm,28*mm]),Spacer(1,6*mm),p("نمودارهای فاز اول",h1),make_table(["نمودار","فایل"],[["توزیع نمرهٔ MOCATOTS","figures/phase1/02_moca_distribution.svg"],["پراکنش MOCATOTS و حجم دوطرفهٔ Entorhinal با روند خطی","figures/phase1/08_moca_entorhinal_volume_scatter.svg"],["Boxplot نمره برحسب وضعیت شناختی","figures/phase1/06_moca_by_status.svg"],["Heatmap همبستگی Pearson متغیرهای کلیدی","figures/phase1/10_correlation_heatmap.svg"]],[82*mm,81*mm]),Spacer(1,5*mm),p("تفسیر و گام بعد",h1),p("خط روند و همبستگی‌های heatmap خام و توصیفی‌اند؛ اثر سن و تحصیلات را کنترل نمی‌کنند و رابطهٔ علّی را نشان نمی‌دهند. در فاز مدل‌سازی، برای هر شاخص MRI جداگانه مدل چندمتغیرهٔ MOCATOTS ~ شاخص انتورینال + سن + تحصیلات تعریف شود؛ بررسی فروض، باقیمانده‌ها، گمشدگی و هم‌زمانی MRI/UDS پیش از تفسیر لازم است. نمونه، زیرمجموعهٔ بالینی/پژوهشی NACC است و نمایندهٔ تصادفی جمعیت عمومی نیست.",body),Spacer(1,3*mm),p("کد تحلیل: src/phase1_analysis.py | جدول‌ها و نتایج ماشین‌خوان: reports/phase1/ | نمودارها: figures/phase1/",small)]
doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=21*mm,bottomMargin=19*mm,title="فاز اول؛ NACC سالمندان و MoCA/MRI انتورینال",author="تحلیل توصیفی بازتولیدپذیر")
doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer)
shutil.copyfile(PDF,ROOT/"reports/phase1.pdf")
print(f"Created {PDF} and reports/phase1.pdf")
