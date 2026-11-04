import os, hashlib, json, re, html, time, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
FEEDS = {
 "the-gioi": [("VnExpress","https://vnexpress.net/rss/the-gioi.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/the-gioi.rss"),("VnEconomy","https://vneconomy.vn/kinh-te-the-gioi.rss"),("BBC Business","https://feeds.bbci.co.uk/news/business/rss.xml"),("CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html"),("MarketWatch","https://feeds.content.dowjones.io/public/rss/mw_topstories")],
 "thoi-su": [("VnExpress","https://vnexpress.net/rss/thoi-su.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/thoi-su.rss"),("Thanh Niên","https://thanhnien.vn/rss/thoi-su.rss"),("VietNamNet","https://vietnamnet.vn/thoi-su.rss")],
 "kinh-te-vn": [("VnExpress","https://vnexpress.net/rss/kinh-doanh.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/kinh-doanh.rss"),("Thanh Niên","https://thanhnien.vn/rss/kinh-te.rss"),("VietNamNet","https://vietnamnet.vn/kinh-doanh.rss"),("CafeF","https://cafef.vn/vi-mo-dau-tu.rss"),("VnEconomy","https://vneconomy.vn/dau-tu.rss")],
 "tai-chinh": [("CafeF","https://cafef.vn/thi-truong-chung-khoan.rss"),("CafeF","https://cafef.vn/tai-chinh-ngan-hang.rss"),("VnEconomy","https://vneconomy.vn/chung-khoan.rss"),("VnEconomy","https://vneconomy.vn/tai-chinh.rss"),("CNBC","https://www.cnbc.com/id/10000664/device/rss/rss.html")],
 "bat-dong-san": [("VnExpress","https://vnexpress.net/rss/bat-dong-san.rss"),("CafeF","https://cafef.vn/bat-dong-san.rss")],
}
MAXPER=40
def clean(s):
    s=html.unescape(html.unescape(re.sub(r"<[^>]+>"," ",s or ""))); return re.sub(r"\s+"," ",s).strip()
def img_of(it, raw):
    for el in it:
        t=el.tag.split('}')[-1]
        if t in("thumbnail","content") and el.get("url"): return el.get("url")
        if t=="enclosure" and "image" in (el.get("type") or "image"): return el.get("url")
    m=re.search(r'<img[^>]+src=["\']([^"\']+)',raw or "")
    return m.group(1) if m else ""
items, ok, bad = [], [], []
for ch, feeds in FEEDS.items():
    for src,url in feeds:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 BachSuThong"})
            data=urllib.request.urlopen(req,timeout=20).read()
            root=ET.fromstring(data); n=0
            for it in root.iter("item"):
                g=lambda k:(it.findtext(k) or "")
                desc=g("description"); link=g("link").strip()
                if not link: continue
                try: ts=int(parsedate_to_datetime(g("pubDate")).timestamp())
                except Exception: ts=int(time.time())
                s=clean(desc); s=s[:220]+("…" if len(s)>220 else "")
                items.append(dict(title=clean(g("title")),summary=s,image=img_of(it,desc),source=src,link=link,time=ts,channel=ch))
                n+=1
                if n>=MAXPER: break
            ok.append([src,url,n])
        except Exception as e:
            bad.append([src,url,str(e)[:80]])
seen,out=set(),[]
now=time.time()
for x in sorted(items,key=lambda x:-x["time"]):
    k=re.sub(r"\W+","",x["title"].lower())[:60]
    if not x["title"] or k in seen or x["link"] in seen or x["time"]>now+3600: continue
    seen.add(k); seen.add(x["link"]); out.append(x)

PERCH=100
_c={}
_o=[]
for x in out:
    _c[x["channel"]]=_c.get(x["channel"],0)+1
    if _c[x["channel"]]<=PERCH: _o.append(x)
out=_o
TOPN=12
ART="cache/articles";os.makedirs(ART,exist_ok=True);os.makedirs("data",exist_ok=True)
for x in out: x["id"]=hashlib.sha1(x["link"].encode()).hexdigest()[:12]
want=[]
for ch in FEEDS:
    want+= [x for x in out if x["channel"]==ch][:TOPN]
def extract(x):
    p=f"{ART}/{x['id']}.json"
    if os.path.exists(p): return True
    try:
        import trafilatura
        req=urllib.request.Request(x["link"],headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})
        raw=urllib.request.urlopen(req,timeout=20).read().decode("utf-8","ignore")
        txt=trafilatura.extract(raw,include_comments=False,include_tables=False,favor_precision=True) or ""
        paras=[q.strip() for q in txt.split("\n") if len(q.strip())>40][:8]
        if not paras: return False
        body=[];n=0
        for q in paras:
            if n>2500: break
            body.append(q);n+=len(q)
        json.dump(dict(id=x["id"],paras=body,more=len(paras)>len(body) or len(txt)>n),open(p,"w"),ensure_ascii=False)
        return True
    except Exception as e:
        return False
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex: res=list(ex.map(extract,want))
for x,r in zip(want,res):
    if r: x["full"]=1
keep={x["id"] for x in out if x.get("full")}
for f in os.listdir(ART):
    if f[:-5] not in keep: os.remove(ART+"/"+f)
for x in out:
    if not x.get("full") and os.path.exists(f"{ART}/{x['id']}.json"): x["full"]=1
print("articles:",sum(res),"/",len(want))
json.dump(dict(updated=int(now),sources_ok=ok,sources_failed=bad,items=out),open("data/news.json","w"),ensure_ascii=False)
print(len(out),"items; ok",len(ok),"failed",bad)
