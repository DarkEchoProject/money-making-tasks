#!/usr/bin/env python3
import json, re, html, os, urllib.request, urllib.parse, mimetypes
from pathlib import Path
from datetime import datetime, timezone

BLOG='https://money-making-tasks.blogspot.com'
ROOT=Path('.')
UA='Mozilla/5.0 (compatible; MoneyMakingTasksMigration/1.0)'

CSS='''
:root{--bg:#f5f7fb;--card:#fff;--text:#182033;--muted:#667085;--accent:#1668dc;--line:#e6eaf0;--max:1100px}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:Tahoma,Arial,sans-serif;line-height:1.85}.container{max-width:var(--max);margin:auto;padding:0 18px}.site-header{background:#111827;color:#fff;padding:26px 0 18px}.site-header h1{margin:0;font-size:28px}.site-header p{margin:4px 0;color:#d1d5db}.site-header a{color:#fff;text-decoration:none}.nav{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}.nav a{background:#1f2937;padding:7px 12px;border-radius:8px}.hero{padding:28px 0}.hero-card,.card,.article{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 7px 24px rgba(16,24,40,.05)}.hero-card{padding:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:18px;padding-bottom:32px}.card{padding:20px}.card h3{margin-top:0}.card a{color:var(--accent);text-decoration:none}.date,.meta{font-size:13px;color:var(--muted)}.article{padding:26px;margin:28px auto}.article img{max-width:100%;height:auto;border-radius:8px}.article iframe{max-width:100%}.article a{color:var(--accent)}.article-content{overflow-wrap:anywhere}.site-footer{background:#111827;color:#cbd5e1;margin-top:40px;padding:24px 0}.footer-links{display:flex;gap:15px;flex-wrap:wrap}.footer-links a{color:#fff}.notice{background:#fff7ed;border:1px solid #fed7aa;padding:12px 14px;border-radius:10px;margin:16px 0}@media(max-width:600px){.site-header h1{font-size:23px}.article{padding:18px}}
'''


def get(url, binary=False):
    req=urllib.request.Request(url, headers={'User-Agent':UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data=r.read()
        return data if binary else data.decode('utf-8','replace')

def fetch_feed(kind='posts'):
    url=f'{BLOG}/feeds/{kind}/default?alt=json&max-results=500'
    try:
        return json.loads(get(url)).get('feed',{}).get('entry',[])
    except Exception as e:
        print('feed failed',kind,e)
        return []

def esc(s): return html.escape(s or '', quote=True)

def clean_text(markup):
    txt=re.sub(r'<script.*?</script>',' ',markup or '',flags=re.I|re.S)
    txt=re.sub(r'<style.*?</style>',' ',txt,flags=re.I|re.S)
    txt=re.sub(r'<[^>]+>',' ',txt)
    txt=html.unescape(txt)
    txt=re.sub(r'\s+',' ',txt).strip()
    return txt

def entry_alt(e):
    for l in e.get('link',[]):
        if l.get('rel')=='alternate': return l.get('href','')
    return ''

def entry_title(e): return e.get('title',{}).get('$t','بدون عنوان').strip()

def entry_content(e):
    return (e.get('content') or e.get('summary') or {}).get('$t','')

def entry_date(e):
    x=(e.get('published') or e.get('updated') or {}).get('$t','')
    return x[:10]

def localize_images(markup, slug):
    imgs=re.findall(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])',markup,flags=re.I)
    n=0
    for pre,url,post in imgs:
        if url.startswith('data:'): continue
        absu=urllib.parse.urljoin(BLOG,url)
        if not absu.startswith(('http://','https://')): continue
        try:
            data=get(absu,binary=True)
            if len(data)>8_000_000: continue
            ctype=mimetypes.guess_type(urllib.parse.urlparse(absu).path)[0] or 'image/jpeg'
            ext=mimetypes.guess_extension(ctype) or Path(urllib.parse.urlparse(absu).path).suffix or '.jpg'
            if ext=='.jpe': ext='.jpg'
            n+=1
            name=f'{slug}-{n}{ext}'
            target=ROOT/'assets'/'images'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            markup=markup.replace(pre+url+post,pre+f'/assets/images/{name}'+post,1)
        except Exception as ex:
            print('image failed',absu,ex)
    return markup

def shell(title, inner, prefix=''):
    nav=f'''<nav class="nav"><a href="{prefix}index.html">الرئيسية</a><a href="{prefix}privacy.html">سياسة الخصوصية</a><a href="{prefix}contact.html">تواصل معنا</a></nav>'''
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} | طرق الربح من الإنترنت</title><meta name="description" content="مقالات وشروحات عن طرق الربح من الإنترنت وتجارب الأدوات والمنصات."><link rel="stylesheet" href="{prefix}assets/style.css"></head><body><header class="site-header"><div class="container"><h1><a href="{prefix}index.html">طرق الربح من الإنترنت</a></h1><p>أرشيف المدونة القديمة بعد نقلها إلى GitHub Pages</p>{nav}</div></header><main class="container">{inner}</main><footer class="site-footer"><div class="container"><div class="footer-links"><a href="{prefix}privacy.html">سياسة الخصوصية</a><a href="{prefix}contact.html">تواصل معنا</a></div><p>© 2026 طرق الربح من الإنترنت</p></div></footer></body></html>'''

def write(path,text):
    p=ROOT/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding='utf-8')

def rel_prefix(path):
    parts=Path(path).parts
    return '../'*(len(parts)-1)

posts=fetch_feed('posts')
items=[]
for i,e in enumerate(posts,1):
    url=entry_alt(e)
    path=urllib.parse.urlparse(url).path.lstrip('/')
    if not path or not path.endswith('.html'):
        path=f'posts/post-{i}.html'
    title=entry_title(e); content=entry_content(e); date=entry_date(e)
    slug=re.sub(r'[^A-Za-z0-9]+','-',Path(path).stem).strip('-') or f'post-{i}'
    content=localize_images(content,slug)
    prefix=rel_prefix(path)
    article=f'<article class="article"><header><h1>{esc(title)}</h1><div class="meta">{esc(date)}</div></header><div class="article-content">{content}</div></article>'
    write(path,shell(title,article,prefix))
    items.append((date,title,path,clean_text(content)[:190]))

items.sort(reverse=True,key=lambda x:x[0])
cards=[]
for date,title,path,summary in items:
    cards.append(f'<article class="card"><h3><a href="{esc(path)}">{esc(title)}</a></h3><p>{esc(summary)}…</p><div class="date">{esc(date)}</div></article>')
hero='''<section class="hero"><div class="hero-card"><h2>مقالات وشروحات الربح من الإنترنت</h2><p>هذا أرشيف مدونتي القديمة بعد نقله من Blogger. بعض المعلومات والروابط قديمة وسيتم تحديث المحتوى تدريجيًا.</p></div></section>'''
write('index.html',shell('طرق الربح من الإنترنت',hero+'<section class="grid">'+''.join(cards)+'</section>',''))
write('assets/style.css',CSS)
write('privacy.html',shell('سياسة الخصوصية','''<article class="article"><h1>سياسة الخصوصية</h1><p>نحترم خصوصية الزوار. قد تستخدم الخدمات الخارجية المرتبطة بالموقع ملفات تعريف الارتباط أو تقنيات مشابهة وفق سياساتها الخاصة. لا نطلب منك إرسال معلومات حساسة عبر الموقع.</p><p>قد تحتوي المقالات القديمة على روابط إحالة أو روابط لخدمات خارجية. تحقق دائمًا من شروط الخدمة الحالية قبل التسجيل أو الدفع.</p></article>'''))
write('contact.html',shell('تواصل معنا','''<article class="article"><h1>تواصل معنا</h1><p>البريد الإلكتروني: <a href="mailto:alinasser00001@gmail.com">alinasser00001@gmail.com</a></p><p>يمكنك أيضًا التواصل عبر حساباتنا الاجتماعية التي سنضيفها بعد مراجعة الموقع.</p></article>'''))
write('404.html',shell('الصفحة غير موجودة','<article class="article"><h1>الصفحة غير موجودة</h1><p><a href="/">العودة إلى الصفحة الرئيسية</a></p></article>'))
write('robots.txt','User-agent: *\nAllow: /\n')
write('.nojekyll','')

base='https://darkechoproject.github.io/money-making-tasks/'
urls=[base]+[urllib.parse.urljoin(base,p) for _,_,p,_ in items]+[base+'privacy.html',base+'contact.html']
now=datetime.now(timezone.utc).date().isoformat()
sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{esc(u)}</loc><lastmod>{now}</lastmod></url>\n' for u in urls)+'</urlset>\n'
write('sitemap.xml',sitemap)
print('Generated',len(items),'posts')
