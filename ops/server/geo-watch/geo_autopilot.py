#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
geo_autopilot.py — الحلقة المقفولة لتحسين الظهور في محركات البحث الذكية.

بيقرأ آخر قياس من geo_watch، بيشوف الأسئلة اللي اختفينا منها، وبيولّد
مقالات تجاوب عليها بالظبط، وبيحطّها في طابور النشر الموجود (queue.json)
اللي بينشر واحد يومياً مع IndexNow. القياس الجاي بيقول أثّرت ولا لأ.

    python3 geo_autopilot.py --dry-run    # يولّد ويعرض من غير ما يضيف
    python3 geo_autopilot.py              # يولّد ويضيف للطابور
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request

from google.oauth2 import service_account
from google.auth.transport.requests import Request as GRequest

BASE = '/opt/geo-watch'
QUEUE = '/opt/seo/queue.json'
BLOG_DIR = '/var/www/montessori-ksa/blog'
HISTORY = f'{BASE}/history.jsonl'
LOG_FILE = f'{BASE}/autopilot.log'
MAILGW = 'http://127.0.0.1:8099/send'

SA_KEY = '/opt/gstatus/billing-key.json'
PROJECT = 'n8n-server-47538'
LOCATION = 'us-central1'
MODEL = 'gemini-2.5-flash'
GEMINI_URL = (f'https://{LOCATION}-aiplatform.googleapis.com/v1/projects/'
              f'{PROJECT}/locations/{LOCATION}/publishers/google/models/'
              f'{MODEL}:generateContent')

# ── مسار مجاني بديل: مفتاح Gemini API من AI Studio ──
# لو /etc/nursery-gemini.key موجود وفيه مفتاح، النداء بيروح للطبقة المجانية
# (generativelanguage.googleapis.com) بنفس الموديل ونفس جسم الطلب — صفر فوترة
# Vertex. لو الملف مش موجود بنكمّل على Vertex زي الأول.
GEMINI_KEY_FILE = '/etc/nursery-gemini.key'
# gemini-2.5-flash مقفول على المفاتيح الجديدة (404 «no longer available to new
# users» — مقيس 13/8). flash-latest بيتابع الأحدث تلقائياً فما بيتقفلش.
# ⛔ الحصة المجانية = 20 نداء/يوم **لكل موديل على حدة**
# (GenerateRequestsPerDayPerProjectPerModel-FreeTier=20، مقيس 15/8 من رد 429).
# يعني كل موديل في السلسلة = ٢٠ نداء إضافية.
#
# مقيس 15/8 بتوليد حقيقي على نفس المفتاح:
#   gemini-3.6-flash        ✓ 23ث، مقال عدّى الحاجز كامل  ← الأساسي
#   gemini-flash-latest     ✓ شغّال (بيتابع الأحدث = 3.7 حالياً) ← احتياطي
#   gemini-3.5-flash        ✗ 503 ضغط
#   gemini-2.5-flash        ✗ 404 (مقفول على المفاتيح الجديدة)
#   gemini-flash-lite-latest ✗ بيطلّع مقالات قصيرة وبيدّعي إننا نستقبل رضّع
#
# ⚠️ 'gemini-flash-latest' هدف متحرّك — جوجل نقلته لـ3.7 من غير إشعار.
# عشان كده الأساسي مثبّت برقم صريح.
FREE_MODELS = ['gemini-3.6-flash', 'gemini-flash-latest']
FREE_MODEL = FREE_MODELS[0]   # للتوافق مع أي كود قديم
GEMINI_FREE_BASE = 'https://generativelanguage.googleapis.com/v1beta/models/'
GEMINI_FREE_URL = f'{GEMINI_FREE_BASE}{FREE_MODEL}:generateContent'

# سقف الفشل المتتالي: من غيره جولة واحدة بتاكل الـ٢٠ نداء كلها وتطلّع مقال واحد
# (اتقاس 15/8: جولة --dry-run حرقت ١٥ نداء وطلّعت مقال واحد).
MAX_CONSEC_FAIL = 3


def _free_key():
    try:
        k = open(GEMINI_KEY_FILE).read().strip()
        return k or None
    except Exception:
        return None


BRIEF = f'{BASE}/keyword-brief.json'


def load_brief():
    """كلمات Ubersuggest المستهدفة — بأحجام بحث حقيقية، بتتحدّث يومياً.

    دفاعي بالكامل: أي مشكلة في الملف = نرجّع None والمولّد يشتغل زي الأول.
    """
    try:
        with open(BRIEF, encoding='utf-8') as f:
            d = json.load(f)
        kws = [k for k in d.get('target_keywords') or []
               if isinstance(k, dict) and k.get('keyword')]
        if not kws:
            return None
        kws.sort(key=lambda k: (k.get('priority') or 9,
                                -(k.get('volume') or 0)))
        pos = d.get('positioning') or {}
        return {'keywords': kws,
                'angles': d.get('content_angles') or [],
                'avoid': d.get('avoid') or [],
                'positioning': [v for v in (pos.get('rule'),
                                            pos.get('apply')) if v]}
    except Exception as e:
        log(f'  (تنبيه) keyword-brief مش متقري: {e} — بنكمّل من غيره')
        return None


def brief_block(brief):
    """يحوّل الموجز لنص يتحقن في طلب التوليد."""
    if not brief:
        return ''
    lines = []
    for k in brief['keywords'][:6]:
        v = k.get('volume')
        vt = f" (حجم بحث {v}/شهر)" if v else ''
        lines.append(f"- {k['keyword']}{vt}")
    out = ''
    # التموضع بييجي الأول — ده قيد على شكل المقال كله مش مجرد كلمات
    if brief.get('positioning'):
        out += ('\n\n⚠️ قاعدة تموضع ملزمة (تسبق كل ما دونها):\n'
                + '\n'.join(f'- {x}' for x in brief['positioning']))
    out += ('\n\nكلمات مستهدفة بأحجام بحث حقيقية من Ubersuggest — '
            'استخدم أقربها للسؤال بشكل طبيعي في العنوان وأول فقرة، '
            'ولا تحشُها حشواً:\n' + '\n'.join(lines))
    if brief['angles']:
        out += ('\nزوايا محتوى مطلوبة:\n'
                + '\n'.join(f'- {a}' for a in brief['angles'][:3]))
    if brief['avoid']:
        out += ('\nممنوع (فوق القواعد أعلاه):\n'
                + '\n'.join(f'- {a}' for a in brief['avoid'][:3]))
    return out


TARGET_PENDING = 8      # نحافظ على الطابور مليان لحد كده
MAX_PER_RUN = 4         # سقف التوليد في الجولة الواحدة
CATS = ['local', 'montessori', 'choose', 'dev', 'activities']

# ── حاجز الحقائق: ده كل اللي مسموح يتقال عن المنشأة ──
sys.path.insert(0, '/opt/nursery-facts')
from facts import FACTS, RULES, BANS, MUST  # مرجع الحقائق المشترك

SCHEMA = """أعد JSON فقط (بدون أي شرح أو علامات كود) بهذا الشكل بالضبط:
{
 "slug": "english-kebab-case-unique",
 "cat": "واحدة من: local | montessori | choose | dev | activities",
 "title": "عنوان عربي جذاب أقل من 70 حرفاً",
 "targetKeyword": "الكلمة المستهدفة",
 "secondaryKeywords": ["3 إلى 5 كلمات"],
 "metaDescription": "وصف عربي 140-160 حرف",
 "wordCount": 1000,
 "related": [],
 "bodyHtml": "<p>...</p><h2>...</h2><p>...</p><ul><li>...</li></ul> — 900 كلمة فأكثر، HTML بسيط: p, h2, h3, ul, li, strong فقط. بدون <html> أو <head>. ⚠️ ممنوع تماماً أي خصائص داخل الوسوم (لا class ولا style ولا dir)، وممنوع استخدام علامة التنصيص المزدوجة داخل النص — استخدم « » بدلاً منها. أي علامة تنصيص مزدوجة زائدة تُفسد الـJSON.",
 "faq": [{"q":"سؤال","a":"إجابة في 2-3 جمل"}]
}
اجعل faq من 4 إلى 6 أسئلة، وأول سؤال هو سؤال المستخدم نفسه."""



def _escape_stray_quotes(s):
    """يهرّب أي " شاردة جوّه سلسلة JSON.

    سبب الكسر الأشيع (مقيس 15/8: ٣ من ٥ توليدات): النموذج بيحط خصائص HTML
    زي <p class="x"> جوّه bodyHtml من غير تهريب، فالـ" بتقفل السلسلة بدري
    والتحليل بيقع بـ«Expecting ',' delimiter».

    الحيلة: علامة التنصيص تبقى إقفال حقيقي **بس لو** أول حرف غير فراغ بعدها
    واحد من , : } ] — غير كده فهي جوّه النص ولازم تتهرّب.
    """
    out, instr, esc = [], False, False
    for i, c in enumerate(s):
        if not instr:
            out.append(c)
            if c == '"':
                instr = True
            continue
        if esc:
            out.append(c)
            esc = False
            continue
        if c == '\\':
            out.append(c)
            esc = True
            continue
        if c == '"':
            j = i + 1
            while j < len(s) and s[j] in ' \t\r\n':
                j += 1
            if j >= len(s) or s[j] in ',:}]':
                out.append(c)
                instr = False
            else:
                out.append('\\"')      # شاردة → نهرّبها
            continue
        out.append(c)
    return ''.join(out)


def parse_json(txt):
    """تحليل متسامح: النموذج أحياناً بيزوّد كلام قبل/بعد الـJSON."""
    txt = txt.strip()
    txt = re.sub(r'^```(?:json)?|```$', '', txt, flags=re.M).strip()
    # strict=False: النموذج بيسيب أسطر جديدة خام جوّه السلاسل
    try:
        return json.loads(txt, strict=False)
    except json.JSONDecodeError:
        pass
    i = txt.find('{')
    if i < 0:
        raise ValueError('مفيش JSON في الرد')
    depth, instr, esc = 0, False, False
    for j in range(i, len(txt)):
        c = txt[j]
        if instr:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(txt[i:j + 1], strict=False)
                except json.JSONDecodeError:
                    break   # نكمّل للإصلاح الشارد تحت
    # آخر ملاذ: نهرّب علامات التنصيص الشاردة ونعيد المحاولة — بيوفّر نداء
    # من الحصة اليومية الضيقة (٢٠/موديل) بدل ما نرمي التوليد كله.
    try:
        fixed = _escape_stray_quotes(txt[i:])
        # raw_decode بيقف عند نهاية أول كائن سليم فالكلام الزايد بعده ما يضرّش
        return json.JSONDecoder(strict=False).raw_decode(fixed)[0]
    except (json.JSONDecodeError, ValueError):
        pass
    raise ValueError('JSON ناقص')


def log(*a):
    line = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(str(x) for x in a)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass
    print(line, flush=True)


def token():
    c = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=['https://www.googleapis.com/auth/cloud-platform'])
    c.refresh(GRequest())
    return c.token


def _post(url, body, hdrs, timeout=240):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers=hdrs)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def _call_gemini(tok, body):
    """نداء بسلسلة موديلات وتراجع.

    503 = ضغط مؤقت ← نعيد المحاولة على نفس الموديل.
    429 = الحصة اليومية (٢٠/موديل) خلصت ← ننتقل للموديل اللي بعده فوراً،
          إعادة المحاولة مالهاش لازمة لأن العدّاد يومي.
    """
    _k = _free_key()
    if not _k:
        return _post(GEMINI_URL, body,
                     {'Authorization': f'Bearer {tok}',
                      'Content-Type': 'application/json'})

    hdrs = {'x-goog-api-key': _k, 'Content-Type': 'application/json'}
    last = None
    for model in FREE_MODELS:
        url = f'{GEMINI_FREE_BASE}{model}:generateContent'
        for attempt, wait in enumerate((0, 8, 20), 1):
            if wait:
                time.sleep(wait)
            try:
                return _post(url, body, hdrs)
            except urllib.error.HTTPError as e:
                last = e
                if e.code == 429:
                    log(f'    ({model}: الحصة اليومية خلصت — الموديل اللي بعده)')
                    break
                if e.code in (500, 502, 503, 504):
                    log(f'    ({model}: {e.code} ضغط — محاولة {attempt}/3)')
                    continue
                raise
    raise last if last else RuntimeError('كل الموديلات فشلت')


def gen(tok, prompt_text, existing_slugs, brief=None):
    """يولّد مقال JSON يجاوب على سؤال بعينه."""
    ask = (f'{FACTS}\n{RULES}{brief_block(brief)}\n\n'
           f'اكتب مقالاً عربياً كاملاً يجيب على هذا السؤال الذي يسأله الأهالي '
           f'لمساعدات الذكاء الاصطناعي:\n«{prompt_text}»\n\n'
           f'slugs مستخدمة بالفعل (اختر واحداً مختلفاً): {", ".join(sorted(existing_slugs)[:60])}\n\n'
           f'{SCHEMA}')
    body = {'contents': [{'role': 'user', 'parts': [{'text': ask}]}],
            'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 20000,
                                 'responseMimeType': 'application/json'}}
    r = _call_gemini(tok, body)
    cand = r['candidates'][0]
    if cand.get('finishReason') not in (None, 'STOP'):
        raise ValueError(f"توليد ناقص: {cand.get('finishReason')}")
    txt = ''.join(p.get('text', '') for p in cand['content']['parts'] if not p.get('thought'))
    return parse_json(txt)


def validate(a, existing_slugs):
    """بيرجع قايمة أسباب الرفض — فاضية يعني سليم."""
    bad = []
    for f in ('slug', 'cat', 'title', 'targetKeyword', 'metaDescription',
              'bodyHtml', 'faq'):
        if not a.get(f):
            bad.append(f'حقل ناقص: {f}')
    if bad:
        return bad
    if not re.fullmatch(r'[a-z0-9-]+', a['slug']):
        bad.append(f"slug غير صالح: {a['slug']}")
    if a['slug'] in existing_slugs:
        bad.append(f"slug مكرر: {a['slug']}")
    if a['cat'] not in CATS:
        bad.append(f"فئة غير معروفة: {a['cat']}")
    if len(re.sub(r'<[^>]+>', ' ', a['bodyHtml']).split()) < 450:
        bad.append('المقال قصير جداً')
    if not isinstance(a.get('faq'), list) or len(a['faq']) < 3:
        bad.append('faq أقل من 3 أسئلة')
    blob = a['bodyHtml'] + ' ' + a['metaDescription'] + ' ' + a['title'] + ' ' + \
        ' '.join(f"{x.get('q','')} {x.get('a','')}" for x in (a.get('faq') or []))
    for name, rx in BANS:
        m = rx.search(blob)
        if m:
            bad.append(f'{name}: «{m.group(0)[:45]}»')
    if not MUST.search(blob):
        bad.append('ما ذكرش نطاق أعمارنا (٢–٥) صراحةً')
    return bad


def latest_run():
    with open(HISTORY) as f:
        lines = [l for l in f if l.strip()]
    if not lines:
        raise SystemExit('مفيش قياسات لسه — شغّل geo_watch الأول')
    return json.loads(lines[-1])


def send_mail(subject, html):
    b = json.dumps({'subject': subject, 'html': html},
                   ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(MAILGW, data=b,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max', type=int, default=MAX_PER_RUN)
    args = ap.parse_args()

    run = latest_run()
    queue = json.loads(open(QUEUE, encoding='utf-8').read())
    pending = [a for a in queue if not a.get('published')]
    slugs = {a['slug'] for a in queue}
    slugs |= {d for d in os.listdir(BLOG_DIR)
              if os.path.isdir(os.path.join(BLOG_DIR, d))}

    need = max(0, TARGET_PENDING - len(pending))
    n = min(need, args.max)
    log(f'الطابور: {len(pending)} منتظر · الهدف {TARGET_PENDING} · هنولّد {n}')
    if n == 0:
        log('الطابور مليان — مفيش توليد')
        return 0

    # الفجوات: الأولوية للفئات اللي ظهورها أقل
    misses = [r for r in run['results']
              if 'error' not in r and not r['mentioned']]
    order = sorted(run['by_category'].items(), key=lambda x: x[1])
    rank = {c: i for i, (c, _) in enumerate(order)}
    misses.sort(key=lambda r: rank.get(r['category'], 99))

    tok = token()
    brief = load_brief()
    if brief:
        log(f'موجز الكلمات: {len(brief["keywords"])} كلمة مستهدفة '
            f'(أعلاها: {brief["keywords"][0]["keyword"]})')
    made, rejected = [], []
    consec_fail = 0
    for r in misses:
        if len(made) >= n:
            break
        if consec_fail >= MAX_CONSEC_FAIL:
            log(f'وقفنا بعد {consec_fail} فشل متتالي — بنحمي الحصة اليومية '
                f'(٢٠ نداء/موديل). الباقي هيتولّد الجولة الجاية.')
            break
        p = r['prompt']
        log(f'  توليد: {p[:55]}')
        try:
            a = gen(tok, p, slugs, brief)
        except Exception as e:
            consec_fail += 1
            log(f'    ✗ فشل التوليد: {e}')
            rejected.append((p, [str(e)[:120]]))
            continue
        consec_fail = 0
        bad = validate(a, slugs)
        if bad:
            log(f'    ✗ مرفوض: {"; ".join(bad)}')
            rejected.append((p, bad))
            continue
        a['related'] = []
        a['_geo_prompt'] = p
        a['_geo_added'] = datetime.date.today().isoformat()
        made.append(a)
        slugs.add(a['slug'])
        log(f"    ✓ {a['slug']} ({a['cat']})")
        time.sleep(2)

    if made and not args.dry_run:
        shutil.copy2(QUEUE, f'{QUEUE}.bak-autopilot-{time.strftime("%Y%m%d-%H%M%S")}')
        queue.extend(made)
        tmp = QUEUE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=1)
        os.replace(tmp, QUEUE)
        log(f'اتضاف للطابور: {len(made)} — الطابور بقى {len(pending)+len(made)}')

    rows = ''.join(
        f'<li><b>{a["title"]}</b><br><span style="color:#666">يجاوب على: {a["_geo_prompt"]}</span>'
        f'<br><span style="color:#888;font-size:12px">/blog/{a["slug"]}/ · {a["cat"]}</span></li>'
        for a in made)
    rej = ''.join(f'<li>{p}<br><span style="color:#c0392b;font-size:12px">{"; ".join(b)}</span></li>'
                  for p, b in rejected)
    html = f"""<div dir="rtl" style="font-family:system-ui,Tahoma,sans-serif;line-height:1.7">
<h2>الطيّار الآلي — محتوى جديد للفجوات</h2>
<p>آخر قياس: ظهور <b>{run['visibility_pct']}%</b>. الفئات الأضعف اتاخدت الأولوية.</p>
<h3>اتضاف للطابور ({len(made)})</h3><ul>{rows or '<li>ولا واحد</li>'}</ul>
{f'<h3>مرفوض من حاجز الحقائق ({len(rejected)})</h3><ul>{rej}</ul>' if rejected else ''}
<p style="color:#888;font-size:12px">بينشر واحد يومياً عبر الطابور الموجود مع IndexNow.
الرفض معناه إن المولّد كسر قاعدة (سعر مخترع أو عمر غلط) — وده الحاجز شغّال صح.</p></div>"""
    if not args.dry_run:
        try:
            send_mail(f'الطيّار الآلي — {len(made)} مقال جديد للفجوات', html)
        except Exception as e:
            log(f'✗ إيميل: {e}')
    else:
        log('(تجربة — مفيش إضافة ولا إيميل)')
        for a in made:
            log(f"   {a['slug']}: {a['title']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
