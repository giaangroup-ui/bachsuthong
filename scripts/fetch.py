import json, re, html, time, urllib.request, xml.etree.ElementTree as ET
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
json.dump(dict(updated=int(now),sources_ok=ok,sources_failed=bad,items=out),open("data/news.json","w"),ensure_ascii=False)
print(len(out),"items; ok",len(ok),"failed",bad)
