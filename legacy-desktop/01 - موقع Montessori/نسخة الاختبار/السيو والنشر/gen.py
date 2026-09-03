# -*- coding: utf-8 -*-
import json, re, pathlib, html as H, datetime

ROOT = pathlib.Path("/private/tmp/claude-501/-Users-mohamedmontaser/aa580398-b142-4789-a9f2-6ffc95184412/scratchpad")
arts   = json.loads((ROOT/"seo/articles.json").read_text())
briefs = json.loads((ROOT/"seo/briefs.json").read_text())
BLOG   = ROOT/"landing/blog"
BLOG.mkdir(parents=True, exist_ok=True)
SITE = "https://montessori-ksa.com"

# ---- slug remap (writers renamed some slugs) : brief slug -> actual slug, index-aligned ----
remap = { briefs[i]['slug']: arts[i]['slug'] for i in range(len(arts)) }
actual = { a['slug']: a for a in arts }
brief_by_actual = { arts[i]['slug']: briefs[i] for i in range(len(arts)) }

def fix_links(s):
    for old,new in remap.items():
        if old != new:
            s = s.replace(f'/blog/{old}/', f'/blog/{new}/')
    return s

# ---- categories ----
CATS = {
 'best-montessori-nursery-jeddah':'local','nursery-jeddah':'local','nursery-al-faisaliyah-jeddah':'local',
 'best-nurseries-jeddah-2026':'local','nursery-prices-jeddah':'local','quran-nursery-jeddah':'local',
 'bilingual-nursery-jeddah':'local','licensed-accredited-nursery-jeddah':'local','summer-program-jeddah':'local',
 'child-care-hourly-jeddah':'local',
 'what-is-montessori-method':'montessori','montessori-benefits-for-children':'montessori',
 'montessori-vs-traditional-education':'montessori','montessori-activities-at-home':'montessori',
 'nursery-entry-age-guide':'choose','difference-nursery-preschool-kindergarten':'choose',
 'what-is-kindergarten-stages-goals-saudi':'choose','how-to-choose-nursery-jeddah':'choose',
 'signs-child-ready-for-nursery':'choose','preparing-child-first-day-nursery':'choose',
 'separation-anxiety-in-nursery':'choose','is-nursery-good-for-child':'choose',
 'child-independence-development':'dev','learning-through-play':'dev','motor-skills-development-children':'dev',
 'healthy-nutrition-for-children':'dev','social-skills-in-children':'dev','quran-memorization-for-kids':'dev',
 'bilingual-education-benefits-children':'dev','school-readiness-skills':'dev',
}
CAT_META = {
 'local':    {'name':'حضانتنا في جدة','desc':'أدلّة عن حضانتنا ومونتيسوري وبرامجنا في حي الفيصلية بجدة','order':1},
 'montessori':{'name':'منهج مونتيسوري','desc':'ما هو منهج مونتيسوري وفوائده وكيف يتعلّم به طفلك','order':2},
 'choose':   {'name':'اختيار الحضانة والمراحل','desc':'كيف تختارين الحضانة، والأعمار، والفرق بين المراحل، وتهيئة طفلك','order':3},
 'dev':      {'name':'تنمية الطفل','desc':'مهارات ولغة وقرآن وتغذية وأنشطة لنموّ طفلك','order':4},
}

MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
def ar_date(d): return f"{d.day} {MONTHS[d.month-1]} {d.year}"
BASE = datetime.date(2026,7,4)

# assign meta (index 0 = newest)
meta = {}
for i,a in enumerate(arts):
    d = BASE - datetime.timedelta(days=i*2)
    wc = a.get('wordCount') or 1200
    meta[a['slug']] = {'date':d, 'iso':d.isoformat(), 'ar':ar_date(d),
                       'rt':max(4, round(wc/180)), 'cat':CATS[a['slug']]}

def esc(s): return H.escape(s, quote=True)

# ---- shared header / footer ----
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

def related_block(slug):
    links = brief_by_actual[slug].get('internalLinks') or []
    seen=[]; out=[]
    for l in links:
        t = remap.get(l, l)
        if t in actual and t!=slug and t not in seen:
            seen.append(t)
    # top up from same category if fewer than 3
    if len(seen)<3:
        for a in arts:
            s=a['slug']
            if s!=slug and CATS[s]==CATS[slug] and s not in seen:
                seen.append(s)
            if len(seen)>=3: break
    seen=seen[:3]
    if not seen: return ''
    cards=''
    for s in seen:
        a=actual[s]; cm=CAT_META[CATS[s]]
        cards+=f'''<a class="rel-card" href="/blog/{s}/">
      <span class="rel-card__cat">{esc(cm['name'])}</span>
      <span class="rel-card__title">{esc(a['title'])}</span>
      <span class="rel-card__go">اقرأ المقال ←</span>
    </a>'''
    return f'''<nav class="related" aria-label="مقالات ذات صلة">
  <h2>مقالات قد تهمّك</h2>
  <div class="related__grid">{cards}</div>
</nav>'''

def faq_block(faq):
    if not faq: return ''
    items=''
    for f in faq:
        items+=f'''<details class="faq__item">
      <summary>{esc(f['q'])}</summary>
      <div class="faq__a"><p>{esc(f['a'])}</p></div>
    </details>'''
    return f'''<section class="faq" aria-label="الأسئلة الشائعة">
  <h2>الأسئلة الشائعة</h2>
  {items}
</section>'''

def jsonld(a, m):
    slug=a['slug']; url=f"{SITE}/blog/{slug}/"
    b=brief_by_actual[slug]
    kws=[a.get('targetKeyword','')]+(b.get('secondaryKeywords') or [])
    blogposting={
      "@context":"https://schema.org","@type":"BlogPosting","@id":url+"#article",
      "headline":a['title'],"description":a['metaDescription'],
      "inLanguage":"ar","url":url,"mainEntityOfPage":{"@type":"WebPage","@id":url},
      "datePublished":m['iso'],"dateModified":m['iso'],
      "author":{"@type":"Organization","name":"حضانة مونتيسوري","url":SITE+"/"},
      "publisher":{"@type":"Organization","name":"حضانة مونتيسوري","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
      "image":SITE+"/logo.png","keywords":", ".join([k for k in kws if k]),
      "articleSection":CAT_META[m['cat']]['name'],"wordCount":a.get('wordCount')
    }
    faqpage={"@context":"https://schema.org","@type":"FAQPage",
      "mainEntity":[{"@type":"Question","name":f['q'],
        "acceptedAnswer":{"@type":"Answer","text":f['a']}} for f in (a.get('faq') or [])]}
    crumbs={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
      {"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE+"/"},
      {"@type":"ListItem","position":2,"name":"المدوّنة","item":SITE+"/blog/"},
      {"@type":"ListItem","position":3,"name":a['title'],"item":url}]}
    j=lambda o: json.dumps(o, ensure_ascii=False, separators=(',',':'))
    return (f'<script type="application/ld+json">{j(blogposting)}</script>\n'
            f'<script type="application/ld+json">{j(faqpage)}</script>\n'
            f'<script type="application/ld+json">{j(crumbs)}</script>')

def article_page(a):
    slug=a['slug']; m=meta[slug]; cm=CAT_META[m['cat']]
    b=brief_by_actual[slug]
    kws=[a.get('targetKeyword','')]+(b.get('secondaryKeywords') or [])
    url=f"{SITE}/blog/{slug}/"
    body=fix_links(a['bodyHtml'])
    title=a['title']
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(title)}</title>
<meta name="description" content="{esc(a['metaDescription'])}"/>
<meta name="keywords" content="{esc(', '.join([k for k in kws if k]))}"/>
<meta name="author" content="حضانة مونتيسوري"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{url}"/>
<meta name="geo.region" content="SA-02"/>
<meta name="geo.placename" content="Jeddah"/>
<meta name="geo.position" content="21.5795281;39.194829"/>
<meta property="og:type" content="article"/>
<meta property="og:site_name" content="حضانة مونتيسوري"/>
<meta property="og:title" content="{esc(title)}"/>
<meta property="og:description" content="{esc(a['metaDescription'])}"/>
<meta property="og:url" content="{url}"/>
<meta property="og:image" content="{SITE}/logo.png"/>
<meta property="og:locale" content="ar_SA"/>
<meta property="article:published_time" content="{m['iso']}"/>
<meta property="article:section" content="{esc(cm['name'])}"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{esc(title)}"/>
<meta name="twitter:description" content="{esc(a['metaDescription'])}"/>
<meta name="twitter:image" content="{SITE}/logo.png"/>
<link rel="icon" href="/logo.png"/>
<link rel="apple-touch-icon" href="/logo.png"/>
<link rel="stylesheet" href="/assets/fonts.css?v=2"/>
<link rel="stylesheet" href="/assets/app.css?v=10"/>
<link rel="stylesheet" href="/assets/blog.css?v=1"/>
{jsonld(a,m)}
</head>
<body class="blog-body">
{header()}
<main class="container article-wrap">
  <nav class="crumbs" aria-label="مسار التنقّل">
    <a href="/">الرئيسية</a><span>›</span><a href="/blog/">المدوّنة</a><span>›</span><span class="crumbs__cur">{esc(cm['name'])}</span>
  </nav>
  <article class="article">
    <header class="article__head">
      <a class="article__cat" href="/blog/#{m['cat']}">{esc(cm['name'])}</a>
      <h1>{esc(title)}</h1>
      <div class="article__meta">
        <span class="am-author"><img src="/logo.png" alt=""/> فريق حضانة مونتيسوري</span>
        <span class="am-dot">·</span><time datetime="{m['iso']}">{esc(m['ar'])}</time>
        <span class="am-dot">·</span><span>{m['rt']} دقائق قراءة</span>
      </div>
    </header>
    <div class="article__body">
{body}
    </div>
    {faq_block(a.get('faq'))}
    {cta_card(a.get('targetKeyword',''))}
    {related_block(slug)}
  </article>
</main>
{footer()}
</body>
</html>'''

# ---- write article pages ----
n=0
for a in arts:
    d = BLOG/a['slug']; d.mkdir(exist_ok=True)
    (d/"index.html").write_text(article_page(a), encoding='utf-8')
    n+=1

# ---- blog index ----
def index_card(a, big=False):
    s=a['slug']; m=meta[s]; cm=CAT_META[m['cat']]
    cls="bcard bcard--big" if big else "bcard"
    return f'''<a class="{cls}" href="/blog/{s}/">
      <span class="bcard__cat">{esc(cm['name'])}</span>
      <h3 class="bcard__title">{esc(a['title'])}</h3>
      <p class="bcard__desc">{esc(a['metaDescription'])}</p>
      <span class="bcard__meta"><time datetime="{m['iso']}">{esc(m['ar'])}</time> · {m['rt']} دقائق</span>
    </a>'''

# section per category
sections=''
for ckey,cm in sorted(CAT_META.items(), key=lambda kv: kv[1]['order']):
    cat_arts=[a for a in arts if CATS[a['slug']]==ckey]
    cat_arts.sort(key=lambda a: meta[a['slug']]['date'], reverse=True)
    cards=''.join(index_card(a) for a in cat_arts)
    sections+=f'''<section class="bsec" id="{ckey}">
    <div class="bsec__head"><h2>{esc(cm['name'])}</h2><p>{esc(cm['desc'])}</p></div>
    <div class="bgrid">{cards}</div>
  </section>'''

# featured = 3 newest local/money
featured=[a for a in arts if CATS[a['slug']]=='local'][:3]
feat_cards=''.join(index_card(a, big=True) for a in featured)

nav_chips=''.join(f'<a class="chip-nav" href="#{k}">{esc(v["name"])}</a>'
                  for k,v in sorted(CAT_META.items(), key=lambda kv: kv[1]['order']))

blog_ld=json.dumps({
  "@context":"https://schema.org","@type":"Blog","@id":SITE+"/blog/#blog",
  "name":"مدوّنة حضانة مونتيسوري جدة","inLanguage":"ar","url":SITE+"/blog/",
  "description":"مقالات تربوية للأمهات في جدة عن مونتيسوري، اختيار الحضانة، أعمار الأطفال، وتنمية المهارات.",
  "publisher":{"@type":"Organization","name":"حضانة مونتيسوري","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
  "blogPost":[{"@type":"BlogPosting","headline":a['title'],"url":f"{SITE}/blog/{a['slug']}/","datePublished":meta[a['slug']]['iso']} for a in arts]
}, ensure_ascii=False, separators=(',',':'))
crumb_ld=json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
  {"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE+"/"},
  {"@type":"ListItem","position":2,"name":"المدوّنة","item":SITE+"/blog/"}]},ensure_ascii=False,separators=(',',':'))

index_html=f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>مدوّنة حضانة مونتيسوري جدة | مقالات تربوية للأمهات</title>
<meta name="description" content="مدوّنة حضانة مونتيسوري في جدة: مقالات عن منهج مونتيسوري، اختيار الحضانة، سن دخول الحضانة، تحفيظ القرآن، وتنمية مهارات طفلك — بأسلوب تربوي موثوق."/>
<meta name="keywords" content="حضانة جدة, حضانة مونتيسوري جدة, مونتيسوري, حضانة حي الفيصلية, اختيار حضانة, سن دخول الحضانة, تربية الاطفال"/>
<meta name="author" content="حضانة مونتيسوري"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{SITE}/blog/"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="حضانة مونتيسوري"/>
<meta property="og:title" content="مدوّنة حضانة مونتيسوري جدة | مقالات تربوية للأمهات"/>
<meta property="og:description" content="مقالات عن مونتيسوري واختيار الحضانة وتنمية طفلك — من حضانة مونتيسوري في جدة."/>
<meta property="og:url" content="{SITE}/blog/"/>
<meta property="og:image" content="{SITE}/logo.png"/>
<meta property="og:locale" content="ar_SA"/>
<link rel="icon" href="/logo.png"/>
<link rel="stylesheet" href="/assets/fonts.css?v=2"/>
<link rel="stylesheet" href="/assets/app.css?v=10"/>
<link rel="stylesheet" href="/assets/blog.css?v=1"/>
<script type="application/ld+json">{blog_ld}</script>
<script type="application/ld+json">{crumb_ld}</script>
</head>
<body class="blog-body">
{header()}
<main>
  <section class="blog-hero">
    <div class="container">
      <span class="eyebrow">مدوّنة حضانة مونتيسوري · جدة</span>
      <h1>معرفة تربوية تُعينكِ على أفضل بداية لطفلك</h1>
      <p class="lead">مقالات موثوقة بالعربية عن منهج مونتيسوري، واختيار الحضانة المناسبة، وأعمار الأطفال، وتحفيظ القرآن، وتنمية المهارات — من فريق حضانة مونتيسوري في حي الفيصلية بجدة.</p>
      <div class="chip-nav-row">{nav_chips}</div>
    </div>
  </section>
  <div class="container">
    <section class="bsec bsec--feat">
      <div class="bsec__head"><h2>الأكثر أهمية للأمهات في جدة</h2></div>
      <div class="bgrid bgrid--feat">{feat_cards}</div>
    </section>
    {sections}
  </div>
</main>
{footer()}
</body>
</html>'''
(BLOG/"index.html").write_text(index_html, encoding='utf-8')

# ---- sitemap ----
def urlblock(loc, mod, freq, pr):
    return f'''  <url>
    <loc>{loc}</loc>
    <lastmod>{mod}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{pr}</priority>
  </url>'''
today="2026-07-05"
urls=[]
urls.append(f'''  <url>
    <loc>{SITE}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
    <xhtml:link rel="alternate" hreflang="ar" href="{SITE}/"/>
    <xhtml:link rel="alternate" hreflang="en" href="{SITE}/en/"/>
  </url>''')
urls.append(urlblock(f"{SITE}/en/", today, "weekly", "0.9"))
urls.append(urlblock(f"{SITE}/blog/", today, "weekly", "0.9"))
for a in sorted(arts, key=lambda a: meta[a['slug']]['date'], reverse=True):
    pr = "0.8" if CATS[a['slug']]=='local' else "0.7"
    urls.append(urlblock(f"{SITE}/blog/{a['slug']}/", meta[a['slug']]['iso'], "monthly", pr))
sitemap=f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
{chr(10).join(urls)}
</urlset>'''
(ROOT/"landing/sitemap.xml").write_text(sitemap, encoding='utf-8')

# ---- report ----
print(f"✓ wrote {n} article pages + blog index")
print(f"✓ sitemap.xml : {len(arts)+3} urls")
# validate internal links resolve
bad=0
for a in arts:
    for l in re.findall(r'/blog/([a-z0-9-]+)/', fix_links(a['bodyHtml'])):
        if l not in actual: bad+=1; print("  ! dangling link in",a['slug'],"->",l)
print(f"✓ internal-link check: {bad} dangling")
print("cats:", {k:sum(1 for s in CATS.values() if s==k) for k in CAT_META})
