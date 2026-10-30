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
story += [Spacer(1,23*mm),p("شناخت داده و توصیف آماری",title),p("تحلیل فاز اول | زیرمجموعهٔ NACC: UDS + MRI",subtitle),Spacer(1,11*mm)]
story += [p("پرسش پروژه",h1),p("در این زیرمجموعهٔ تحویلی، نمرهٔ خام MoCA و ضخامت قشر انتورینال چگونه توزیع شده‌اند و این توزیع‌ها در گروه‌های وضعیت شناختی ثبت‌شده در UDS چه تفاوت‌های توصیفی دارند؟",body),Spacer(1,3*mm)]
story += [make_table(["شاخص","نتیجهٔ توصیفی"],[["افراد یکتای متصل‌شده",fa_num(data["linkage"]["common_participants"])],["فایل UDS و فایل MRI", "۱٬۲۳۷ ردیف در هر فایل"],["افراد دارای هر دو وجه",fa_num(data["linkage"]["participants_with_both_MRI_and_UDS_valid_main_variables"])],["میانگین سن در UDS",fa_num(data["summary_statistics"]["NACCAGE"]["mean"])+" سال"],["میانگین نمرهٔ MOCATOTS معتبر",fa_num(data["summary_statistics"]["MOCATOTS_valid_0_30"]["mean"])],["میانگین ضخامت دوطرفهٔ انتورینال",fa_num(data["summary_statistics"]["ENTORHINAL_BILATERAL_AVGTH_mm"]["mean"])+" میلی‌متر"]],[72*mm,91*mm]),Spacer(1,8*mm)]
story += [p("دامنه و احتیاط در تفسیر",h1),p("این گزارش توصیفی است و آزمون فرض یا ادعای علّی ارائه نمی‌کند. داده‌ها از یک زیرمجموعهٔ بالینی/پژوهشی NACC می‌آیند و نمونهٔ احتمالی جمعیت عمومی نیستند؛ بنابراین درصدهای این فایل را نباید شیوع جمعیتی دانست. نام فایل UDS نشان می‌دهد داده پردازش‌شده و imputed است، ولی روش جایگذاری و نقاب دادهٔ اولیه همراه فایل نیست.",body),Spacer(1,4*mm),p("تاریخ تولید: ۳۰ اکتبر ۲۰۲۶",small),PageBreak()]

story += [p("۱. منبع داده، طرح مطالعه و واحد تحلیل",h1),p("منبع پروژه، زیرمجموعهٔ آماده‌شدهٔ National Alzheimer’s Coordinating Center (NACC) است. دو فایل تحویلی شامل UDS با متغیرهای جمعیت‌شناختی، پزشکی، عملکردی و شناختی و MRI با اندازه‌گیری‌های ساختاری قشری هستند. این مجموعه یک مطالعهٔ مشاهده‌ای در نمونهٔ بالینی/پژوهشی است؛ افراد به‌صورت تصادفی از جمعیت عمومی انتخاب نشده‌اند.",body),p("در هر دو فایل ۱٬۲۳۷ ردیف و ۱٬۲۳۷ شناسهٔ یکتا وجود دارد. شناسهٔ NACCID به‌صورت یک‌به‌یک استفاده شد. همهٔ شناسه‌ها در فایل مقابل پیدا شدند؛ عدم تطابق صفر بود. کد NACCUDSD در دو فایل برای هر فرد همسان بود. این شواهد، اتصال شناسه‌ای را پشتیبانی می‌کند، اما تاریخ مراجعه و تاریخ MRI در فایل‌ها نیست؛ بنابراین هم‌زمانی بالینی دو اندازه‌گیری را نمی‌توان اثبات کرد.",body),Figure("linkage"),p("شکل ۱. شمار افرادِ یکتا در اتصال UDS و MRI. فقط یک ردیف برای هر شناسه در فایل موجود است؛ شناسه یا تاریخ مراجعه در فایل‌ها نیست.",caption),p("تعداد ردیف‌ها را باید تعداد رکوردهای تحویلی دانست. فایل‌ها برای محاسبهٔ تعداد واقعی مراجعه‌ها یا انتخاب نخستین/نزدیک‌ترین مراجعه اطلاعات کافی ندارند. در فاز بعد، قاعدهٔ انتخاب یک مشاهده برای هر فرد باید حفظ شود و فاصلهٔ زمانی MRI–UDS، در صورت دسترسی به تاریخ‌ها، گزارش شود.",body),PageBreak()]

story += [p("۲. نقشهٔ متغیرها و قواعد کیفیت داده",h1),make_table(["وجه و متغیر","نوع/مقیاس","نقش و تعریف در این تحلیل"],[["NACCAGE","کمی پیوسته؛ سال","سن در رکورد UDS"],["EDUC","کمی گسسته؛ سال تحصیل","کد ۹۹ طبق کدنامه به‌صورت نامعلوم کنار گذاشته شد"],["MOCATOTS","نمرهٔ کمی؛ ۰ تا ۳۰","MoCA خام؛ متغیر شناختی اصلی"],["NACCUDSD","طبقه‌ای؛ ۴ سطح","گروه‌بندی وضعیت شناختی"],["CDRSUM و CDRGLOB","نمره/طبقهٔ مرتب","شدت بالینی و طبقه‌بندی CDR"],["ENTORHINAL_AVGTH","کمی پیوسته؛ میلی‌متر","ضخامت متوسط چپ و راست؛ میانگین دوطرفه تعریف‌شده در پروژه"],["ENTORHINAL_GVOL","کمی پیوسته؛ میلی‌متر مکعب","حجم مادهٔ خاکستری؛ ممیزی وجه MRI"]],[49*mm,40*mm,74*mm]),Spacer(1,4*mm),p("قواعد ممیزی و تصمیم تحلیلی",h2),p("در سلول‌های دادهٔ اصلی مقدار خالی ثبت‌شده وجود نداشت. این به معنی نبود گمشدگی در دادهٔ اولیه نیست، چون فایل UDS جایگذاری‌شده است و روش/نقاب اولیه موجود نیست. مطابق کدنامهٔ NACC، EDUC=99 در دو نفر نامعلوم است و از محاسبهٔ سال‌های تحصیل کنار گذاشته شد. برای MOCATOTS فقط بازهٔ معتبر ۰ تا ۳۰ نگه داشته شد: ۹ مقدار خارج از این بازه کنار گذاشته شد (کد ۸۸ چهار بار، ۳۰٫۸ یک بار، ۳۴٫۲ یک بار، ۳۸٫۸ یک بار و ۳۹٫۴ دو بار). مقادیر محدود یا گرد نشدند.",body),p("از ۱٬۲۲۸ مقدار معتبر MOCATOTS، تعداد ۲۴۴ مقدار اعشاری است. این ویژگی با فایل جایگذاری‌شده سازگار است، ولی منشأ هر مقدار از فایل حاضر قابل ردیابی نیست؛ بنابراین همهٔ خلاصه‌ها «مقادیر معتبر موجود در فایل پردازش‌شده» هستند، نه دادهٔ خام مشاهده‌شده. به‌عنوان حساسیت توصیفی، محدودکردن محاسبه به مقادیر صحیح n=984 و میانگین ۲۴٫۰۳ می‌دهد؛ این زیرنمونه را نباید observed-case واقعی نامید.",body),p("CDRSUM مجاز است نیم‌نمره داشته باشد. مجموع آن در تمام ۱٬۲۳۷ ردیف با جمع شش مؤلفهٔ CDR برابر بود. دو سلول حجم MRI غیرمثبت دیده شد: یک حجم انتورینال چپ و یک حجم posterior cingulate چپ برابر صفر؛ برای حجم انتورینال در این گزارش از مقدار صفر استفاده نشد. برای ضخامت قشری حد بالای دلخواه وضع نشد؛ مستندات رسمی برای این ستون‌ها دامنهٔ عددی تعیین نکرده‌اند.",body),PageBreak()]

def desc_rows(keys):
    out=[]
    for key,label,unit in keys:
        s=data["summary_statistics"][key]
        out.append([label,fa_num(s["n"],0),fa_num(s["mean"]),fa_num(s["sd"]),fa_num(s["median"]),fa_num(s["q1"])+" تا "+fa_num(s["q3"]),fa_num(s["min"])+" تا "+fa_num(s["max"]),unit])
    return out

story += [p("۳. آمار توصیفی نمونه و متغیرهای اصلی",h1),make_table(["متغیر","n","میانگین","انحراف معیار","میانه","چارک ۱–۳","کمینه–بیشینه","واحد"],desc_rows([("NACCAGE","سن","سال"),("EDUC_years","تحصیلات","سال"),("MOCATOTS_valid_0_30","MoCA خام","نمره"),("CDRSUM","CDR Sum of Boxes","نمره"),("ENTORHINAL_BILATERAL_AVGTH_mm","ضخامت انتورینال دوطرفه","میلی‌متر")]),[29*mm,9*mm,17*mm,21*mm,16*mm,25*mm,27*mm,19*mm]),Spacer(1,6*mm),Figure("age"),p("شکل ۲. توزیع سن ثبت‌شده در UDS؛ دامنهٔ مشاهده‌شده ۴۱ تا ۹۱ سال است.",caption),Figure("moca"),p("شکل ۳. توزیع مقادیر MOCATOTS در بازهٔ معتبر. وجود مقادیر اعشاری بازتاب فایل پردازش‌شده است.",caption),PageBreak()]

frequency_rows=[]
labels_fa={"SEX":{"1":"مرد","2":"زن"},"NACCUDSD":{"1":"وضعیت شناختی طبیعی","2":"اختلال، بدون MCI","3":"اختلال شناختی خفیف (MCI)","4":"دمانس"},"CDRGLOB":{"0.0":"بدون اختلال","0.5":"مشکوک","1.0":"خفیف","2.0":"متوسط","3.0":"شدید"}}
for variable in ("SEX","NACCUDSD","CDRGLOB"):
    for e in data["categorical_frequencies"][variable]:
        frequency_rows.append([variable,e["code"],labels_fa[variable].get(e["code"],e["label"]),fa_num(e["n"],0),fa_pct(e["percent"])])
group_table=make_table(["وضعیت","n گروه","MoCA n؛ میانه (IQR)","ضخامت n؛ میانه (IQR), mm"],[[v["label"],fa_num(v["n"],0),fa_num(v["MOCATOTS"].get("n",0),0)+"؛ "+fa_num(v["MOCATOTS"].get("median"))+" ("+fa_num(v["MOCATOTS"].get("q1"))+"–"+fa_num(v["MOCATOTS"].get("q3"))+")",fa_num(v["ENTORHINAL_BILATERAL_AVGTH_mm"].get("n",0),0)+"؛ "+fa_num(v["ENTORHINAL_BILATERAL_AVGTH_mm"].get("median"))+" ("+fa_num(v["ENTORHINAL_BILATERAL_AVGTH_mm"].get("q1"))+"–"+fa_num(v["ENTORHINAL_BILATERAL_AVGTH_mm"].get("q3"))+")"] for v in data["by_NACCUDSD"].values()],[36*mm,18*mm,52*mm,50*mm])
story += [p("۴. فراوانی متغیرهای طبقه‌ای و مقایسهٔ توصیفی",h1),make_table(["متغیر","کد","طبقه","تعداد","درصد"],frequency_rows,[27*mm,15*mm,73*mm,22*mm,25*mm]),Spacer(1,2*mm),Figure("status",height=72*mm),p("شکل ۴. فراوانی وضعیت شناختی ثبت‌شده در UDS. گروه «اختلال، بدون MCI» فقط ۷ نفر دارد و خلاصهٔ آن بسیار کم‌حجم است.",caption),p("در مقایسهٔ صرفاً توصیفی، میانهٔ MOCATOTS از ۲۶٫۲ در گروه وضعیت شناختی طبیعی (n معتبر=۸۴۲) به ۲۳٫۰ در MCI (n=251) و ۱۷٫۰ در دمانس (n=128) می‌رسد. میانهٔ ضخامت دوطرفهٔ انتورینال به‌ترتیب ۳٫۱۰، ۲٫۹۷ و ۲٫۶۹ میلی‌متر است. این الگو توصیفی است؛ در این فاز، برای اختلاف گروهی آزمون یا استنباط جمعیتی انجام نمی‌شود.",body),KeepTogether(group_table),PageBreak()]

story += [p("۵. خلاصهٔ وجه MRI و پیوند با UDS",h1),p("نام ستون‌های محلی با نام‌های دفترچهٔ رسمی MRI مطابقت دارد: AVGTH ضخامت متوسط بر حسب میلی‌متر و GVOL حجم مادهٔ خاکستری بر حسب میلی‌متر مکعب است. در این پروژه، ضخامت دوطرفه به‌صورت میانگین سادهٔ ستون چپ و راست تعریف شد، مشروط بر اینکه هر دو مقدار مثبت باشند. این خلاصه‌سازی یک تعریف تحلیلی است؛ اسکن‌های دو طرف جداگانه نیز در CSV آمار توصیفی موجود هستند.",body),make_table(["متغیر MRI","n","میانگین","SD","میانه","چارک ۱–۳","دامنه","واحد"],desc_rows([("LH_ENTORHINAL_AVGTH_mm","ضخامت سمت چپ","میلی‌متر"),("RH_ENTORHINAL_AVGTH_mm","ضخامت سمت راست","میلی‌متر"),("ENTORHINAL_BILATERAL_AVGTH_mm","میانگین دوطرفه","میلی‌متر")]),[36*mm,10*mm,17*mm,16*mm,15*mm,24*mm,26*mm,18*mm]),Spacer(1,3*mm),Figure("thickness"),p("شکل ۵. توزیع ضخامت دوطرفهٔ قشر انتورینال؛ n=۱٬۲۳۷. مقادیر دورافتاده حذف نشده‌اند.",caption),Figure("thick_group"),p("شکل ۶. جعبه‌نمودار توصیفی ضخامت قشر انتورینال برحسب کد وضعیت شناختی؛ خطوط جعبه میانه و چارک‌ها را نشان می‌دهند و سبیل‌ها کمینه–بیشینه را.",caption),PageBreak()]

story += [p("۶. رابطهٔ توصیفی دو وجه",h1),Figure("scatter"),p("شکل ۷. پراکنش نمرهٔ MOCATOTS معتبر و ضخامت دوطرفهٔ انتورینال. هر نقطه یک فرد یکتاست. نمودار برای دیدن الگو و پراکندگی است و رابطهٔ علّی یا اثر مستقل را نشان نمی‌دهد.",caption),Figure("moca_group"),p("شکل ۸. توزیع نمرهٔ شناختی در گروه‌ها. تفاوت در پراکندگی، به‌ویژه در گروه دمانس، با صرف یک میانگین خلاصه نمی‌شود. گروه کد ۲ به علت n=۷ باید جداگانه و با احتیاط خوانده شود.",caption),p("سؤال آماری برای ادامهٔ پروژه تثبیت شد: توصیف و مقایسهٔ توزیع MOCATOTS و ضخامت دوطرفهٔ انتورینال در میان گروه‌های NACCUDSD در افراد حاضر در زیرمجموعهٔ چندوجهی. در فازهای بعدی، پیش از هر استنباط باید زمان مراجعه/تصویربرداری، تعریف امتیازهای جایگذاری‌شده، انتخاب مشاهدهٔ مستقل و فروض مدل بررسی شوند.",body),PageBreak()]

story += [p("۷. گمشدگی، انتخاب نمونه و محدودیت تعمیم",h1),make_table(["متغیر اصلی","قابل استفاده n","نامعلوم/خارج دامنه","درصد"],[[r["variable"],fa_num(r["n_valid"],0),fa_num(r["n_unavailable"],0),fa_pct(r["percent_unavailable"])] for r in data["missingness"]],[66*mm,30*mm,43*mm,25*mm]),Spacer(1,6*mm),p("در این اتصال، هر ۱٬۲۳۷ نفر در هر دو فایل حضور دارند؛ پس گروه «فاقد MRI» در دادهٔ تحویلی وجود ندارد. مقایسهٔ افراد دارای MRI و فاقد آن از این زیرمجموعه قابل برآورد نیست. این نبود گروه مقایسه باید به‌عنوان محدودیت انتخاب/دسترس‌پذیری تفسیر شود؛ با صفر پرکردن گروه ساخته نشد.",body),p("فایل‌ها شناسهٔ مراجعه، تاریخ ارزیابی UDS، تاریخ اسکن MRI، شناسهٔ مرکز، متغیرهای کنترل کیفیت MRI، نسخهٔ FreeSurfer و تاریخ دورهٔ گردآوری را ندارند. بنابراین تعداد واقعی مراجعه‌ها، فاصلهٔ زمانی UDS تا MRI، کیفیت عبور اسکن از پروتکل، بازنمایی افراد واجد شرایطی که در فایل نیستند و دورهٔ جمع‌آوری قابل احراز نیست. کدنامهٔ NACC نیز بر این نکته تأکید می‌کند که وضعیت شناختی NACCUDSD تشخیص علت‌شناختی آلزایمر نیست.",body),p("جمعیت مورد تفسیر به همین نمونهٔ چندوجهی موجود در فایل‌ها محدود است. NACC دادهٔ بالینی/پژوهشی گردآوری می‌کند و نمونهٔ حاضر نمونه‌گیری تصادفی ملی نیست. همبستگی یا اختلاف توصیفی احتمالی را نباید علت تلقی کرد. نتایج گروه کوچک کد ۲ و نمره‌های دارای اثر جایگذاری، به‌ویژه عدم قطعیت دارند.",body),PageBreak()]

story += [p("۸. بازتولید، فایل‌ها و منابع",h1),p("کد اصلی در src/phase1_analysis.py تمام اتصال‌ها، قواعد معتبرسازی، جدول‌های CSV، JSON نتایج و نمودارهای SVG را از سه فایل داده می‌سازد. فایل‌های خام بازنویسی نمی‌شوند. پس از اجرای تحلیل، src/build_phase1_report.py گزارش PDF فارسی را می‌سازد.",body),make_table(["خروجی","محتوا"],[["reports/phase1/phase1_results.json","نتایج عددی، ممیزی، فراوانی‌ها و توضیح طراحی"],["reports/phase1/descriptive_statistics.csv","خلاصهٔ توزیع متغیرهای کمی"],["reports/phase1/categorical_frequencies.csv","فراوانی و درصد طبقات"],["reports/phase1/group_summaries.csv","خلاصهٔ توصیفی در گروه‌های NACCUDSD"],["reports/phase1/missingness.csv","شمار و درصد نامعلوم یا خارج دامنه"],["figures/phase1/*.svg","نمودارهای قابل بزرگ‌نمایی، قابل ویرایش و مستقل"],["notebooks/phase1_descriptive_analysis.ipynb","راهنمای اجرا و تفسیر نتایج" ]],[65*mm,99*mm]),Spacer(1,6*mm),p("مراحل اجرا",h2),p("از ریشهٔ پروژه: python3 src/phase1_analysis.py؛ سپس با پایتون محیط GapGPT که ReportLab و ابزار شکل‌دهی فارسی دارد، فایل src/build_phase1_report.py اجرا شود. فایل‌های PDF در مسیرهای reports/phase1.pdf و reports/phase1/report_phase1.pdf قرار می‌گیرند. کتابخانه‌های گزارش PDF در requirements.txt ثبت شده‌اند.",body),p("منابع رسمی",h2),p("NACC UDS Researcher’s Data Dictionary, Version 3.0 (با اصلاحیه‌های بعدی)، صفحه‌های متغیرهای EDUC، MOCATOTS، CDR و NACCUDSD.\nNACC SCAN & CLARiTI MRI Researcher’s Data Dictionary، نام و واحد متغیرهای MRI.\nNACC Researcher’s Guide، بخش پیوند تصویربرداری با مراجعه‌های UDS و محدودیت تفسیر نمونه.",body),p("پیوندهای منابع",h2)]
story += [Paragraph("UDS dictionary: https://files.alz.washington.edu/documentation/uds3-rdd.pdf",ParagraphStyle("ltr",fontName="Helvetica",fontSize=7.2,leading=12,alignment=0,textColor=MUTED)),
          Paragraph("MRI dictionary: https://files.alz.washington.edu/documentation/SCAN-MRI-Imaging-RDD.pdf",ParagraphStyle("ltr",fontName="Helvetica",fontSize=7.2,leading=12,alignment=0,textColor=MUTED)),
          Paragraph("NACC Researcher’s Guide: https://www.naccdata.org/the-nacc-researchers-guide",ParagraphStyle("ltr",fontName="Helvetica",fontSize=7.2,leading=12,alignment=0,textColor=MUTED)),Spacer(1,4*mm),p("سند چارچوب پروژه: amarpr.pdf، بخش فاز اول و الزامات اختصاصی مسیر NACC. تاریخ دریافت داده در پوشهٔ محلی ثبت نشده است.",small)]

doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=21*mm,bottomMargin=19*mm,title="گزارش فاز اول پروژه آمار؛ NACC UDS و MRI",author="تحلیل توصیفی بازتولیدپذیر")
doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer)
# The assignment specifies reports/phase1.pdf; retain the nested project layout too.
shutil.copyfile(PDF,ROOT/"reports/phase1.pdf")
print(f"Created {PDF} and reports/phase1.pdf")
