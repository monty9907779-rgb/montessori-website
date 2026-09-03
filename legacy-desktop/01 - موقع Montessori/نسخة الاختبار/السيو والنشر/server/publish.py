#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ناشِر السيو اليومي — مستقل تماماً على السيرفر (بلا AI وقت التشغيل).
كل يوم: يأخذ أول مقال غير منشور من queue.json، يرندره كصفحة مدوّنة،
يحدّث فهرس المدوّنة + sitemap.xml مباشرة في مجلد الموقع، يُبلّغ IndexNow،
ثم يرسل تقريراً بالبريد عبر ويبهوك n8n. يعمل تحت www-data على montasercloud.

الملفات (على السيرفر):
  /opt/seo/queue.json        قائمة المقالات الجاهزة [{slug,title,cat,targetKeyword,
                             secondaryKeywords,metaDescription,bodyHtml,faq,published?}]
  /opt/seo/indexnow.key      مفتاح IndexNow (سطر واحد)
  /opt/seo/state.json        {last_run, published_count}
  /opt/seo/publish.log       سجل
جذر الموقع: /var/www/montessori-ksa
"""
import json, re, html as H, datetime, pathlib, subprocess, urllib.request, sys

ROOT   = pathlib.Path("/var/www/montessori-ksa")
OPT    = pathlib.Path("/opt/seo")
QUEUE  = OPT/"queue.json"
STATE  = OPT/"state.json"
KEYF   = OPT/"indexnow.key"
LOG    = OPT/"publish.log"
SITE   = "https://montessori-ksa.com"
WEBHOOK= "https://n8n.montessori-ksa.com/webhook/seo-daily-7f3a9c2e41"
CATN   = {'local':'حضانتنا في جدة','montessori':'منهج مونتيسوري',
          'choose':'اختيار الحضانة والمراحل','dev':'تنمية الطفل'}
MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
esc = lambda s: H.escape(str(s), quote=True)

def log(m):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {m}"
    print(line)
    try: LOG.open('a').write(line+"\n")
    except Exception: pass

def ar_date(d): return f"{d.day} {MONTHS[d.month-1]} {d.year}"

# ---------- HTML shells (identical to the site's blog template) ----------
def header():
    return '''<header class="mnav"><div class="mnav__in">
    <a href="/" class="row" style="gap:11px"><img src="/logo.png" alt="حضانة مونتيسوري" style="width:46px;height:46px;border-radius:13px"/>
      <span class="brand-name">حضانة مونتيسوري<small>MONTESSORI · JEDDAH</small></span></a>
    <nav class="links"><a href="/#philosophy">منهجنا</a><a href="/#programs">برامجنا</a>
      <a href="/blog/" aria-current="page">المدوّنة</a><a href="/#gallery">لحظاتنا</a><a href="/#contact">تواصل</a></nav>
    <div class="mnav__cta">
      <a class="lang-toggle" href="/app/" aria-label="تطبيقات الجوال" title="تطبيقات الجوال" style="gap:5px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>تطبيق</a>
      <a class="lang-toggle" href="/en/" lang="en" dir="ltr" aria-label="Switch to English" title="English"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.4 4 5.6 4 9s-1.4 6.6-4 9c-2.6-2.4-4-5.6-4-9s1.4-6.6 4-9z"/></svg>EN</a>
      <a class="btn btn--ghost btn--sm" href="/login/">دخول</a>
      <a class="btn btn--primary btn--sm" href="/#register">احجز زيارة</a>
    </div></div></header>'''

def footer():
    return '''<footer class="foot"><div class="foot__in">
    <div class="soc"><a href="https://www.instagram.com/montessori_nursery/" target="_blank" rel="noopener" aria-label="انستجرام" id="f-ig"></a>
      <a href="https://www.facebook.com/p/Montessori-nursery-100063063920027/" target="_blank" rel="noopener" aria-label="فيسبوك" id="f-fb"></a>
      <a href="https://wa.me/966543068147" target="_blank" rel="noopener" aria-label="واتساب" id="f-wa"></a></div>
    <nav class="fnav"><a href="/">الرئيسية</a><a href="/blog/">المدوّنة</a><a href="/#programs">برامجنا</a>
      <a href="/#register">احجز زيارة</a><a href="/login/">دخول</a></nav>
    <div class="cr">حضانة مونتيسوري © ٢٠٢٦ — جدة، المملكة العربية السعودية · جميع الحقوق محفوظة</div>
  </div></footer>
<button id="totop" aria-label="للأعلى"></button>
<script src="/assets/app.js?v=10"></script>
<script>(function(){var I=NS.icon;['f-ig','f-fb','f-wa'].forEach(function(id,k){var e=document.getElementById(id);if(e)e.innerHTML=I(['camera','users','whatsapp'][k]);});var tt=document.getElementById('totop');if(tt){tt.innerHTML=I('arrowUp');addEventListener('scroll',function(){tt.classList.toggle('show',scrollY>500)},{passive:true});tt.addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});}})();</script>
<script src="/assets/bot.js?v=2" defer></script>'''

def cta(kw):
    return (f'<aside class="cta-card"><div class="cta-card__glow"></div>'
      f'<h2>هل تبحثين عن {esc(kw)}؟</h2>'
      f'<p>حضانة مونتيسوري في حي الفيصلية بجدة — منهج مونتيسوري أصيل مع القرآن والعربية والإنجليزية، بتقييم <strong>4.7★</strong> من 71 مراجعة. احجزي جولة تعريفية وشاهدي بيئتنا المُعدّة عن قرب.</p>'
      f'<div class="cta-card__btns"><a class="btn btn--primary btn--lg" href="/#register">احجزوا زيارة</a>'
      f'<a class="btn btn--soft btn--lg" href="https://wa.me/966543068147" target="_blank" rel="noopener">تواصل واتساب</a></div></aside>')

def faq_block(faq):
    items=''.join(f'<details class="faq__item"><summary>{esc(f["q"])}</summary>'
                  f'<div class="faq__a"><p>{esc(f["a"])}</p></div></details>' for f in (faq or []))
    return f'<section class="faq" aria-label="الأسئلة الشائعة"><h2>الأسئلة الشائعة</h2>{items}</section>'

def related_block(a, allslugs, titles):
    rel=[s for s in (a.get('related') or []) if s in allslugs and s!=a['slug']][:3]
    if len(rel)<3:
        for s in allslugs:
            if s!=a['slug'] and s not in rel: rel.append(s)
            if len(rel)>=3: break
    rel=rel[:3]
    cards=''.join(f'<a class="rel-card" href="/blog/{s}/"><span class="rel-card__cat">{esc(CATN.get(titles.get(s,{}).get("cat","dev")))}</span>'
        f'<span class="rel-card__title">{esc(titles.get(s,{}).get("title",s))}</span>'
        f'<span class="rel-card__go">اقرأ المقال ←</span></a>' for s in rel)
    return f'<nav class="related" aria-label="مقالات ذات صلة"><h2>مقالات قد تهمّك</h2><div class="related__grid">{cards}</div></nav>'

def jsonld(a, iso):
    url=f"{SITE}/blog/{a['slug']}/"; cat=CATN.get(a['cat'],'')
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    j=lambda o: json.dumps(o,ensure_ascii=False,separators=(',',':'))
    bp={"@context":"https://schema.org","@type":"BlogPosting","@id":url+"#article","headline":a['title'],
        "description":a['metaDescription'],"inLanguage":"ar","url":url,"mainEntityOfPage":{"@type":"WebPage","@id":url},
        "datePublished":iso,"dateModified":iso,"author":{"@type":"Organization","name":"حضانة مونتيسوري","url":SITE+"/"},
        "publisher":{"@type":"Organization","name":"حضانة مونتيسوري","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
        "image":SITE+"/logo.png","keywords":", ".join(k for k in kws if k),"articleSection":cat,"wordCount":a.get('wordCount')}
    fq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":f['q'],"acceptedAnswer":{"@type":"Answer","text":f['a']}} for f in (a.get('faq') or [])]}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE+"/"},
        {"@type":"ListItem","position":2,"name":"المدوّنة","item":SITE+"/blog/"},
        {"@type":"ListItem","position":3,"name":a['title'],"item":url}]}
    return (f'<script type="application/ld+json">{j(bp)}</script>\n'
            f'<script type="application/ld+json">{j(fq)}</script>\n'
            f'<script type="application/ld+json">{j(bc)}</script>')

def render_article(a, iso, d, allslugs, titles):
    cat=CATN.get(a['cat'],''); url=f"{SITE}/blog/{a['slug']}/"
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    rt=max(4, round((a.get('wordCount') or 1100)/180))
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(a['title'])}</title>
<meta name="description" content="{esc(a['metaDescription'])}"/>
<meta name="keywords" content="{esc(', '.join(k for k in kws if k))}"/>
<meta name="author" content="حضانة مونتيسوري"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{url}"/>
<meta name="geo.region" content="SA-02"/><meta name="geo.placename" content="Jeddah"/><meta name="geo.position" content="21.5795281;39.194829"/>
<meta property="og:type" content="article"/><meta property="og:site_name" content="حضانة مونتيسوري"/>
<meta property="og:title" content="{esc(a['title'])}"/><meta property="og:description" content="{esc(a['metaDescription'])}"/>
<meta property="og:url" content="{url}"/><meta property="og:image" content="{SITE}/logo.png"/><meta property="og:locale" content="ar_SA"/>
<meta property="article:published_time" content="{iso}"/><meta property="article:section" content="{esc(cat)}"/>
<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:title" content="{esc(a['title'])}"/>
<meta name="twitter:description" content="{esc(a['metaDescription'])}"/><meta name="twitter:image" content="{SITE}/logo.png"/>
<link rel="icon" href="/logo.png"/><link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<link rel="stylesheet" href="/assets/fonts.css?v=2"/><link rel="stylesheet" href="/assets/app.css?v=10"/><link rel="stylesheet" href="/assets/blog.css?v=1"/>
{jsonld(a, iso)}
</head><body class="blog-body">
{header()}
<main class="container article-wrap">
  <nav class="crumbs" aria-label="مسار التنقّل"><a href="/">الرئيسية</a><span>›</span><a href="/blog/">المدوّنة</a><span>›</span><span class="crumbs__cur">{esc(cat)}</span></nav>
  <article class="article"><header class="article__head">
    <a class="article__cat" href="/blog/#{a['cat']}">{esc(cat)}</a>
    <h1>{esc(a['title'])}</h1>
    <div class="article__meta"><span class="am-author"><img src="/logo.png" alt=""/> فريق حضانة مونتيسوري</span>
      <span class="am-dot">·</span><time datetime="{iso}">{esc(ar_date(d))}</time><span class="am-dot">·</span><span>{rt} دقائق قراءة</span></div>
  </header>
  <div class="article__body">
{a['bodyHtml']}
  </div>
  {faq_block(a.get('faq'))}
  {cta(a.get('targetKeyword',''))}
  {related_block(a, allslugs, titles)}
  </article>
</main>
{footer()}
</body></html>'''

def indexnow(url):
    try:
        key=KEYF.read_text().strip()
        payload={"host":"montessori-ksa.com","key":key,
                 "keyLocation":f"{SITE}/{key}.txt","urlList":[url]}
        req=urllib.request.Request("https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode(),headers={"Content-Type":"application/json; charset=utf-8"})
        r=urllib.request.urlopen(req,timeout=20); return r.status
    except Exception as ex:
        log(f"indexnow err: {ex}"); return None

def email(subject, html):
    try:
        req=urllib.request.Request(WEBHOOK,data=json.dumps({"subject":subject,"html":html}).encode(),
            headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req,timeout=20); return True
    except Exception as ex:
        log(f"email err: {ex}"); return False

def health():
    ok={}
    for path in ("/","/blog/","/sitemap.xml","/robots.txt"):
        try:
            r=urllib.request.urlopen(SITE+path,timeout=15); ok[path]=r.status
        except Exception as e: ok[path]=str(e)
    return ok

def main():
    today=datetime.date.today(); iso=today.isoformat()
    q=json.loads(QUEUE.read_text())
    pending=[a for a in q if not a.get('published')]
    hz=health()
    hz_ok=all(v==200 for v in hz.values())

    if not pending:
        log("queue empty")
        email("⚠️ [montessori] تقرير السيو اليومي — الطابور فرغ",
              f'<div dir="rtl" style="font-family:Tahoma,sans-serif"><h2 style="color:#b45309">انتهى مخزون المقالات</h2>'
              f'<p>نشرنا كل المقالات الجاهزة. لتزويد الطابور بمقالات جديدة، شغّل توليد دفعة جديدة.</p>'
              f'<p>فحص الصحة: {"✅ سليم" if hz_ok else "⚠️ "+json.dumps(hz,ensure_ascii=False)}</p></div>')
        return

    a=pending[0]
    d=today
    # slugs+titles map for related cards (all queue + assume prior 31 exist)
    titles={x['slug']:{'title':x['title'],'cat':x['cat']} for x in q}
    allslugs=set(titles) | set()  # related may also point to prior slugs; those resolve at browse time
    # render + write article
    art_dir=ROOT/"blog"/a['slug']; art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir/"index.html").write_text(render_article(a, iso, d, set(titles)|{s for s in (a.get('related') or [])}, titles), encoding='utf-8')

    # patch blog index: insert card at top of its category grid
    idxp=ROOT/"blog"/"index.html"; idx=idxp.read_text()
    m=re.search(r'(<section class="bsec" id="%s">.*?<div class="bgrid">)' % a['cat'], idx, re.S)
    if m:
        rt=max(4, round((a.get('wordCount') or 1100)/180))
        card=(f'<a class="bcard" href="/blog/{a["slug"]}/"><span class="bcard__cat">{esc(CATN[a["cat"]])}</span>'
              f'<h3 class="bcard__title">{esc(a["title"])}</h3><p class="bcard__desc">{esc(a["metaDescription"])}</p>'
              f'<span class="bcard__meta"><time datetime="{iso}">{esc(ar_date(d))}</time> · {rt} دقائق</span></a>')
        idx=idx[:m.end(1)]+card+idx[m.end(1):]; idxp.write_text(idx, encoding='utf-8')
    else:
        log(f"WARN: category section {a['cat']} not found in blog index")

    # patch sitemap
    smp=ROOT/"sitemap.xml"; sm=smp.read_text()
    pr="0.8" if a['cat']=='local' else "0.7"
    block=(f'  <url>\n    <loc>{SITE}/blog/{a["slug"]}/</loc>\n    <lastmod>{iso}</lastmod>\n'
           f'    <changefreq>monthly</changefreq>\n    <priority>{pr}</priority>\n  </url>\n</urlset>')
    if a['slug'] not in sm:
        sm=sm.replace("</urlset>", block); smp.write_text(sm, encoding='utf-8')

    # mark published
    a['published']=iso
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')

    # verify live + indexnow
    url=f"{SITE}/blog/{a['slug']}/"
    try: live=urllib.request.urlopen(url,timeout=15).status
    except Exception as e: live=str(e)
    inx=indexnow(url)
    remaining=len([x for x in q if not x.get('published')])

    st={"last_run":iso,"published_count":len([x for x in q if x.get('published')]),"remaining":remaining}
    STATE.write_text(json.dumps(st,ensure_ascii=False,indent=1))

    log(f"published {a['slug']} live={live} indexnow={inx} remaining={remaining}")
    email(f"📈 [montessori] تقرير السيو اليومي — {ar_date(d)}",
      f'<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#22302a;max-width:640px">'
      f'<h2 style="color:#184e3e">📈 تقرير السيو اليومي — {ar_date(d)}</h2>'
      f'<p style="background:#eaf5ef;border-radius:10px;padding:10px 14px"><b>يعمل تلقائياً على السيرفر</b> — مستقل تماماً.</p>'
      f'<h3 style="color:#184e3e">✅ نُشر اليوم</h3><p><a href="{url}">{esc(a["title"])}</a><br/>الكلمة المستهدفة: {esc(a.get("targetKeyword",""))} — الحالة: {live} — IndexNow: {inx}</p>'
      f'<h3 style="color:#184e3e">🩺 فحص الصحة</h3><p>{"✅ الموقع والمدوّنة والخريطة و robots سليمة (200)" if hz_ok else "⚠️ "+esc(json.dumps(hz,ensure_ascii=False))}</p>'
      f'<h3 style="color:#184e3e">📋 المتبقّي في الطابور</h3><p>{remaining} مقال — ' + (f'التالي: {esc(pending[1]["title"])}' if remaining>0 else 'الطابور على وشك الانتهاء — يُنصح بالتزويد') + '</p>'
      f'<hr style="border:none;border-top:1px solid #e9e0cf"/><p style="color:#79857c;font-size:13px">حضانة مونتيسوري · montessori-ksa.com · ناشِر آلي على السيرفر</p></div>')

if __name__=="__main__":
    try: main()
    except Exception as ex:
        log(f"FATAL {ex}")
        try: email("⚠️ [montessori] تقرير السيو اليومي — خطأ", f'<div dir=rtl>حدث خطأ في الناشِر: {esc(ex)}</div>')
        except Exception: pass
        sys.exit(1)
