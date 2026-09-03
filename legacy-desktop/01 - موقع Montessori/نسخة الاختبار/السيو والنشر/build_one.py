# -*- coding: utf-8 -*-
"""Build ONE new blog article page + patch live blog index + sitemap.
Usage: python3 build_one.py new-article.json
new-article.json = {slug,title,metaDescription,targetKeyword,secondaryKeywords,
                    bodyHtml,faq:[{q,a}],wordCount,cat,related:[{slug,title,cat}], date:"YYYY-MM-DD"}
Outputs under work/out/. Never touches existing article pages (no date churn).
"""
import json, sys, re, pathlib, datetime, html as H

D    = pathlib.Path(__file__).parent
WORK = D/"work"
SITE = "https://montessori-ksa.com"
CATN = {'local':'حضانتنا في جدة','montessori':'منهج مونتيسوري',
        'choose':'اختيار الحضانة والمراحل','dev':'تنمية الطفل'}
MONTHS=['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
def esc(s): return H.escape(s, quote=True)
def ar_date(d): return f"{d.day} {MONTHS[d.month-1]} {d.year}"

def header():
    return '''<header class="mnav">
  <div class="mnav__in">
    <a href="/" class="row" style="gap:11px">
      <img src="/logo.png" alt="حضانة مونتيسوري" style="width:46px;height:46px;border-radius:13px"/>
      <span class="brand-name">حضانة مونتيسوري<small>MONTESSORI · JEDDAH</small></span>
    </a>
    <nav class="links">
      <a href="/#philosophy">منهجنا</a>
      <a href="/#programs">برامجنا</a>
      <a href="/blog/" aria-current="page">المدوّنة</a>
      <a href="/#gallery">لحظاتنا</a>
      <a href="/#contact">تواصل</a>
    </nav>
    <div class="mnav__cta">
      <a class="lang-toggle" href="/en/" lang="en" dir="ltr" aria-label="Switch to English" title="English"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.4 4 5.6 4 9s-1.4 6.6-4 9c-2.6-2.4-4-5.6-4-9s1.4-6.6 4-9z"/></svg>EN</a>
      <a class="btn btn--ghost btn--sm" href="/login/">دخول</a>
      <a class="btn btn--primary btn--sm" href="/#register">احجز زيارة</a>
    </div>
  </div>
</header>'''

def footer():
    return '''<footer class="foot">
  <div class="foot__in">
    <div class="soc">
      <a href="https://www.instagram.com/montessori_nursery/" target="_blank" rel="noopener" aria-label="انستجرام" id="f-ig"></a>
      <a href="https://www.facebook.com/p/Montessori-nursery-100063063920027/" target="_blank" rel="noopener" aria-label="فيسبوك" id="f-fb"></a>
      <a href="https://wa.me/966543068147" target="_blank" rel="noopener" aria-label="واتساب" id="f-wa"></a>
    </div>
    <nav class="fnav">
      <a href="/">الرئيسية</a><a href="/blog/">المدوّنة</a><a href="/#programs">برامجنا</a>
      <a href="/#register">احجز زيارة</a><a href="/login/">دخول</a>
    </nav>
    <div class="cr">حضانة مونتيسوري © ٢٠٢٦ — جدة، المملكة العربية السعودية · جميع الحقوق محفوظة</div>
  </div>
</footer>
<button id="totop" aria-label="للأعلى"></button>
<script src="/assets/app.js?v=10"></script>
<script>(function(){var I=NS.icon;
  ['f-ig','f-fb','f-wa'].forEach(function(id,k){var e=document.getElementById(id);if(e)e.innerHTML=I(['camera','users','whatsapp'][k]);});
  var tt=document.getElementById('totop');if(tt){tt.innerHTML=I('arrowUp');
    addEventListener('scroll',function(){tt.classList.toggle('show',scrollY>500)},{passive:true});
    tt.addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});}
})();</script>
<script src="/assets/bot.js?v=2" defer></script>'''

def cta_card(kw):
    return f'''<aside class="cta-card">
  <div class="cta-card__glow"></div>
  <h2>هل تبحثين عن {esc(kw)}؟</h2>
  <p>حضانة مونتيسوري في حي الفيصلية بجدة — منهج مونتيسوري أصيل مع القرآن والعربية والإنجليزية، بتقييم <strong>4.7★</strong> من 71 مراجعة. احجزي جولة تعريفية وشاهدي بيئتنا المُعدّة عن قرب.</p>
  <div class="cta-card__btns">
    <a class="btn btn--primary btn--lg" href="/#register">احجزوا زيارة</a>
    <a class="btn btn--soft btn--lg" href="https://wa.me/966543068147" target="_blank" rel="noopener">تواصل واتساب</a>
  </div>
</aside>'''

def related_block(rel):
    if not rel: return ''
    cards=''.join(f'''<a class="rel-card" href="/blog/{r['slug']}/">
      <span class="rel-card__cat">{esc(CATN[r['cat']])}</span>
      <span class="rel-card__title">{esc(r['title'])}</span>
      <span class="rel-card__go">اقرأ المقال ←</span>
    </a>''' for r in rel[:3])
    return f'''<nav class="related" aria-label="مقالات ذات صلة">
  <h2>مقالات قد تهمّك</h2>
  <div class="related__grid">{cards}</div>
</nav>'''

def faq_block(faq):
    items=''.join(f'''<details class="faq__item">
      <summary>{esc(f['q'])}</summary>
      <div class="faq__a"><p>{esc(f['a'])}</p></div>
    </details>''' for f in (faq or []))
    return f'''<section class="faq" aria-label="الأسئلة الشائعة">
  <h2>الأسئلة الشائعة</h2>
  {items}
</section>'''

def jsonld(a, iso, catname):
    url=f"{SITE}/blog/{a['slug']}/"
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    j=lambda o: json.dumps(o, ensure_ascii=False, separators=(',',':'))
    bp={"@context":"https://schema.org","@type":"BlogPosting","@id":url+"#article",
        "headline":a['title'],"description":a['metaDescription'],"inLanguage":"ar","url":url,
        "mainEntityOfPage":{"@type":"WebPage","@id":url},"datePublished":iso,"dateModified":iso,
        "author":{"@type":"Organization","name":"حضانة مونتيسوري","url":SITE+"/"},
        "publisher":{"@type":"Organization","name":"حضانة مونتيسوري","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
        "image":SITE+"/logo.png","keywords":", ".join(k for k in kws if k),
        "articleSection":catname,"wordCount":a.get('wordCount')}
    fq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":f['q'],"acceptedAnswer":{"@type":"Answer","text":f['a']}} for f in (a.get('faq') or [])]}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE+"/"},
        {"@type":"ListItem","position":2,"name":"المدوّنة","item":SITE+"/blog/"},
        {"@type":"ListItem","position":3,"name":a['title'],"item":url}]}
    return (f'<script type="application/ld+json">{j(bp)}</script>\n'
            f'<script type="application/ld+json">{j(fq)}</script>\n'
            f'<script type="application/ld+json">{j(bc)}</script>')

def article_page(a):
    d=datetime.date.fromisoformat(a['date']); iso=a['date']
    catname=CATN[a['cat']]; url=f"{SITE}/blog/{a['slug']}/"
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    rt=max(4, round((a.get('wordCount') or 1200)/180))
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(a['title'])}</title>
<meta name="description" content="{esc(a['metaDescription'])}"/>
<meta name="keywords" content="{esc(', '.join(k for k in kws if k))}"/>
<meta name="author" content="حضانة مونتيسوري"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{url}"/>
<meta name="geo.region" content="SA-02"/>
<meta name="geo.placename" content="Jeddah"/>
<meta name="geo.position" content="21.5795281;39.194829"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="حضانة مونتيسوري"/>
<meta property="og:title" content="{esc(a['title'])}"/>
<meta property="og:description" content="{esc(a['metaDescription'])}"/>
<meta property="og:url" content="{url}"/>
<meta property="og:image" content="{SITE}/logo.png"/>
<meta property="og:locale" content="ar_SA"/>
<meta property="article:published_time" content="{iso}"/>
<meta property="article:section" content="{esc(catname)}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{esc(a['title'])}"/>
<meta name="twitter:description" content="{esc(a['metaDescription'])}"/>
<meta name="twitter:image" content="{SITE}/logo.png"/>
<link rel="icon" href="/logo.png"/>
<link rel="apple-touch-icon" href="/logo.png"/>
<link rel="stylesheet" href="/assets/fonts.css?v=2"/>
<link rel="stylesheet" href="/assets/app.css?v=10"/>
<link rel="stylesheet" href="/assets/blog.css?v=1"/>
{jsonld(a, iso, catname)}
</head>
<body class="blog-body">
{header()}
<main class="container article-wrap">
  <nav class="crumbs" aria-label="مسار التنقّل">
    <a href="/">الرئيسية</a><span>›</span><a href="/blog/">المدوّنة</a><span>›</span><span class="crumbs__cur">{esc(catname)}</span>
  </nav>
  <article class="article">
    <header class="article__head">
      <a class="article__cat" href="/blog/#{a['cat']}">{esc(catname)}</a>
      <h1>{esc(a['title'])}</h1>
      <div class="article__meta">
        <span class="am-author"><img src="/logo.png" alt=""/> فريق حضانة مونتيسوري</span>
        <span class="am-dot">·</span><time datetime="{iso}">{esc(ar_date(d))}</time>
        <span class="am-dot">·</span><span>{rt} دقائق قراءة</span>
      </div>
    </header>
    <div class="article__body">
{a['bodyHtml']}
    </div>
    {faq_block(a.get('faq'))}
    {cta_card(a.get('targetKeyword',''))}
    {related_block(a.get('related'))}
  </article>
</main>
{footer()}
</body>
</html>'''

def index_card(a, iso, d):
    rt=max(4, round((a.get('wordCount') or 1200)/180))
    return f'''<a class="bcard" href="/blog/{a['slug']}/">
      <span class="bcard__cat">{esc(CATN[a['cat']])}</span>
      <h3 class="bcard__title">{esc(a['title'])}</h3>
      <p class="bcard__desc">{esc(a['metaDescription'])}</p>
      <span class="bcard__meta"><time datetime="{iso}">{esc(ar_date(d))}</time> · {rt} دقائق</span>
    </a>'''

def main():
    a=json.loads(pathlib.Path(sys.argv[1]).read_text())
    d=datetime.date.fromisoformat(a['date'])
    out=WORK/"out"; (out/"blog"/a['slug']).mkdir(parents=True, exist_ok=True)
    # 1) article page
    (out/"blog"/a['slug']/"index.html").write_text(article_page(a), encoding='utf-8')
    # 2) patch blog index: insert card at top of its category grid
    idx=(WORK/"blog-index.html").read_text()
    marker=re.search(r'(<section class="bsec" id="%s">.*?<div class="bgrid">)' % a['cat'], idx, re.S)
    if not marker: raise SystemExit("!! category section not found in blog index")
    card=index_card(a, a['date'], d)
    idx=idx[:marker.end(1)]+card+idx[marker.end(1):]
    (out/"blog"/"index.html").write_text(idx, encoding='utf-8')
    # 3) patch sitemap
    sm=(WORK/"sitemap.xml").read_text()
    pr="0.8" if a['cat']=='local' else "0.7"
    block=f'''  <url>
    <loc>{SITE}/blog/{a['slug']}/</loc>
    <lastmod>{a['date']}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>{pr}</priority>
  </url>
</urlset>'''
    sm=sm.replace("</urlset>", block)
    (out/"sitemap.xml").write_text(sm, encoding='utf-8')
    # 4) register in articles.json (for future internal links)
    arts_p=D/"articles.json"; arts=json.loads(arts_p.read_text())
    arts.append({k:a[k] for k in ('slug','title','targetKeyword','metaDescription','bodyHtml','faq','wordCount') if k in a})
    arts_p.write_text(json.dumps(arts, ensure_ascii=False, indent=1))
    print(f"OK built {a['slug']} | index patched | sitemap urls now:", sm.count("<url>"))

if __name__=="__main__": main()
