import os, hashlib, json, re, html, time, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
FEEDS = {
 "the-gioi": [("VnExpress","https://vnexpress.net/rss/the-gioi.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/the-gioi.rss"),("VnEconomy","https://vneconomy.vn/kinh-te-the-gioi.rss"),("BBC Business","https://feeds.bbci.co.uk/news/business/rss.xml"),("CNBC","https://www.cnbc.com/id/100003114/device/rss/rss.html"),("MarketWatch","https://feeds.content.dowjones.io/public/rss/mw_topstories")],
 "thoi-su": [("VnExpress","https://vnexpress.net/rss/thoi-su.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/thoi-su.rss"),("Thanh Niên","https://thanhnien.vn/rss/thoi-su.rss"),("VietNamNet","https://vietnamnet.vn/thoi-su.rss")],
 "kinh-te-vn": [("VnExpress","https://vnexpress.net/rss/kinh-doanh.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/kinh-doanh.rss"),("Thanh Niên","https://thanhnien.vn/rss/kinh-te.rss"),("VietNamNet","https://vietnamnet.vn/kinh-doanh.rss"),("CafeF","https://cafef.vn/vi-mo-dau-tu.rss"),("VnEconomy","https://vneconomy.vn/dau-tu.rss")],
 "tai-chinh": [("CafeF","https://cafef.vn/thi-truong-chung-khoan.rss"),("CafeF","https://cafef.vn/tai-chinh-ngan-hang.rss"),("VnEconomy","https://vneconomy.vn/chung-khoan.rss"),("VnEconomy","https://vneconomy.vn/tai-chinh.rss"),("CNBC","https://www.cnbc.com/id/10000664/device/rss/rss.html")],
 "ai": [("VnExpress","https://vnexpress.net/rss/so-hoa.rss","ai"),("VnExpress","https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss","ai"),("VnExpress","https://vnexpress.net/rss/goc-nhin.rss","ai"),("Tuổi Trẻ","https://tuoitre.vn/rss/cong-nghe.rss","ai"),("Thanh Niên","https://thanhnien.vn/rss/cong-nghe.rss","ai"),("VietNamNet","https://vietnamnet.vn/cong-nghe.rss","ai"),
   ("TechCrunch","https://techcrunch.com/category/artificial-intelligence/feed/"),("The Verge","https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),("MIT Technology Review","https://www.technologyreview.com/topic/artificial-intelligence/feed"),("Ars Technica","https://feeds.arstechnica.com/arstechnica/technology-lab","ai"),("Wired","https://www.wired.com/feed/tag/ai/latest/rss"),("Import AI","https://importai.substack.com/feed"),("Hugging Face","https://huggingface.co/blog/feed.xml"),("OpenAI","https://openai.com/news/rss.xml")],
 "van-hoa": [("VnExpress","https://vnexpress.net/rss/giai-tri.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/giai-tri.rss"),("Tuổi Trẻ","https://tuoitre.vn/rss/van-hoa.rss"),("Thanh Niên","https://thanhnien.vn/rss/giai-tri.rss"),("Thanh Niên","https://thanhnien.vn/rss/van-hoa.rss"),("VietNamNet","https://vietnamnet.vn/giai-tri.rss"),
   ("Variety","https://variety.com/feed/"),("Rolling Stone","https://www.rollingstone.com/music/feed/"),("Billboard","https://www.billboard.com/feed/"),("The Guardian","https://www.theguardian.com/culture/rss"),("The Guardian","https://www.theguardian.com/film/rss"),("The Guardian","https://www.theguardian.com/books/rss")],
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
AICS=re.compile(r"(?<![\w])(AI|A\.I\.|GenAI|AGI|LLMs?|GPT[-\w]*|ChatGPT|OpenAI|Gemini|Claude|Anthropic|Copilot|DeepSeek|Llama|Mistral|Grok|Nvidia)(?![\w])")
AIWD=re.compile(r"chatbot|machine learning|deep learning|neural net|robot|trí tuệ nhân tạo|học máy|mô hình ngôn ngữ|artificial intelligence",re.I)
class _A:
    def search(self,t): return AICS.search(t) or AIWD.search(t)
AIRE=_A()
SUBS={"ai":[("ai-vn",r"Việt Nam|\bVN\b|tại Việt|người Việt|doanh nghiệp Việt|Bộ KH|Hà Nội|TP\.?HCM|Viettel|FPT|VNPT|MISA"),("ai-model",r"\bmodel|mô hình|GPT|Gemini|Claude|Llama|Grok|DeepSeek|Mistral|chatbot|ra mắt|launch|release|phiên bản|app\b|sản phẩm|Copilot|agent"),("ai-research",r"research|nghiên cứu|paper|study|benchmark|scientist|nhà khoa học|alignment|safety|Import AI|arXiv|lab\b"),("ai-biz",r"doanh nghiệp|startup|đầu tư|funding|raise|billion|tỷ|enterprise|business|công ty|thị trường|Nvidia|chip|data ?cent|ứng dụng|y tế|giáo dục|ngân hàng")],
 "van-hoa":[("vh-music",r"nhạc|ca sĩ|MV\b|album|concert|hòa nhạc|music|song|singer|rapper|Billboard|Grammy|tour\b|K-?pop|ban nhạc|band\b|bài hát"),("vh-film",r"phim|điện ảnh|đạo diễn|diễn viên|film|movie|cinema|box office|doanh thu phòng vé|Oscar|Netflix|series|trailer|liên hoan phim|festival"),("vh-book",r"sách|tiểu thuyết|nhà văn|tác giả|văn học|book|novel|author|poet|thơ|literary"),("vh-star",r"sao\b|showbiz|hoa hậu|người mẫu|scandal|celebrity|kết hôn|ly hôn|hẹn hò|MC\b|Hoa hậu|người đẹp"),("vh-art",r"văn hóa|nghệ thuật|triển lãm|di sản|bảo tàng|sân khấu|kịch|múa|lễ hội|art\b|museum|exhibition|theatre|theater|heritage|painting")]}
def sub_of(ch,txt,src):
    if ch not in SUBS: return ""
    if ch=="ai" and src in("Import AI","MIT Technology Review") and re.search(SUBS["ai"][2][1],txt,re.I): return "ai-research"
    for k,rx in SUBS[ch]:
        if re.search(r"(?<![\w])(?:"+rx+r")(?![\w])",txt,re.I): return k
    return "ai-news" if ch=="ai" else "vh-art"
A="{http://www.w3.org/2005/Atom}"
def iso(s):
    try: return int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp())
    except Exception: return int(time.time())
items, ok, bad = [], [], []
now0=time.time()
for ch, feeds in FEEDS.items():
    for f in feeds:
        src,url=f[0],f[1]; flt=f[2] if len(f)>2 else ""
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 BachSuThong"})
            data=urllib.request.urlopen(req,timeout=20).read()
            root=ET.fromstring(data); n=0
            for it in list(root.iter("item"))+list(root.iter(A+"entry")):
                if it.tag==A+"entry":
                    g=lambda k:(it.findtext(A+k) or "")
                    desc=g("summary") or g("content"); le=[l for l in it.findall(A+"link") if l.get("rel","alternate")=="alternate"]
                    link=(le[0].get("href") if le else "").strip(); ts=iso(g("published") or g("updated"))
                else:
                    g=lambda k:(it.findtext(k) or "")
                    desc=g("description"); link=g("link").strip()
                    try: ts=int(parsedate_to_datetime(g("pubDate")).timestamp())
                    except Exception: ts=int(time.time())
                if not link: continue
                if now0-ts>14*86400: continue
                s=clean(desc); t=clean(g("title"))
                if flt=="ai" and not AIRE.search(t+" "+s): continue
                s=s[:220]+("…" if len(s)>220 else "")
                items.append(dict(title=t,summary=s,image=img_of(it,desc),source=src,link=link,time=ts,channel=ch))
                sb=sub_of(ch,t+" "+s,src)
                if sb: items[-1]["sub"]=sb
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
    k2=(x["channel"],x["source"])
    if x["channel"] in("ai","van-hoa"):
        _c[k2]=_c.get(k2,0)+1
        if _c[k2]>15: continue
    _c[x["channel"]]=_c.get(x["channel"],0)+1
    if _c[x["channel"]]<=PERCH: _o.append(x)
out=_o
TOPN=12; DEEP={"ai","van-hoa"}; DEEPN=20
ART="cache/articles";os.makedirs(ART,exist_ok=True);os.makedirs("data",exist_ok=True)
for x in out: x["id"]=hashlib.sha1(x["link"].encode()).hexdigest()[:12]
want=[]
for ch in FEEDS:
    want+= [x for x in out if x["channel"]==ch][:DEEPN if ch in DEEP else TOPN]
def extract(x):
    p=f"{ART}/{x['id']}.json"
    if os.path.exists(p): return True
    try:
        import trafilatura
        req=urllib.request.Request(x["link"],headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})
        raw=urllib.request.urlopen(req,timeout=20).read().decode("utf-8","ignore")
        txt=trafilatura.extract(raw,include_comments=False,include_tables=False,favor_precision=True) or ""
        dp=x["channel"] in DEEP
        paras=[q.strip() for q in txt.split("\n") if len(q.strip())>40][:15 if dp else 8]
        if not paras: return False
        body=[];n=0
        for q in paras:
            if n>(6000 if dp else 2500): break
            body.append(q);n+=len(q)
        json.dump(dict(id=x["id"],paras=body,more=len(paras)>len(body) or len(txt)>n,words=len(txt.split())),open(p,"w"),ensure_ascii=False)
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
    if x.get("full"):
        try:
            w=json.load(open(f"{ART}/{x['id']}.json")).get("words",0)
            if w: x["rt"]=max(1,round(w/(230 if x["source"] not in("VnExpress","Tuổi Trẻ","Thanh Niên","VietNamNet","CafeF","VnEconomy") else 300)))
        except Exception: pass
print("articles:",sum(res),"/",len(want))
json.dump(dict(updated=int(now),sources_ok=ok,sources_failed=bad,items=out),open("data/news.json","w"),ensure_ascii=False)
print(len(out),"items; ok",len(ok),"failed",bad)
