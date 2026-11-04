# Xếp hạng "tin nóng" + thứ tự danh sách phát (PHẢI khớp hàm ord() trong index.html)
import re, time, unicodedata
STOP=set("cua va cac cho voi trong duoc nhung nay mot nguoi khong da co la tu theo khi ve tai den se hon nam ngay thang sau nhu de vao ra lai nhieu cung dang viec tren the nhat bi the of to in and a for on is with at as by from new that after this are was will has have its it how what why who".split())
HOTW=re.compile(r"khẩn|nóng|bất ngờ|kỷ lục|sập|lao dốc|tăng vọt|bùng nổ|chấn động|breaking|urgent|record|plunge|soar|surge|crash|紧急|突发|暴跌|飙升|创纪录",re.I)
def norm(s):
    s=unicodedata.normalize("NFD",(s or "").lower()); s="".join(c for c in s if unicodedata.category(c)!="Mn").replace("đ","d")
    return s
def toks(t):
    n=norm(t); w={x for x in re.findall(r"[a-z0-9]{3,}",n) if x not in STOP}
    cj=re.findall(r"[\u4e00-\u9fff]",n); w|={cj[i]+cj[i+1] for i in range(len(cj)-1)}
    ws=[x for x in re.findall(r"[a-z0-9]+",n) if x not in STOP]; w|={ws[i]+" "+ws[i+1] for i in range(len(ws)-1)}
    return w
def bigr(t):
    n=norm(t); ws=[x for x in re.findall(r"[a-z0-9]+",n) if x not in STOP and not x.isdigit()]
    cj=re.findall(r"[\u4e00-\u9fff]",n)
    return {ws[i]+" "+ws[i+1] for i in range(len(ws)-1)}|{cj[i]+cj[i+1] for i in range(len(cj)-1)}
def score_hot(items,now=None):
    now=now or time.time(); R=[x for x in items if now-int(x["time"])<12*3600]
    for x in items: x.pop("hot",None)
    T={x["id"]:bigr(x["title"]) for x in R}; df={}
    for v in T.values():
        for k in v: df[k]=df.get(k,0)+1
    lim=max(4,len(R)*.02); T={i:{k for k in v if df[k]<=lim} for i,v in T.items()}
    for x in R:
        srcs={y["source"] for y in R if y["source"]!=x["source"] and len(T[x["id"]]&T[y["id"]])>=2}
        age=(now-int(x["time"]))/3600; hw=bool(HOTW.search(x["title"]))
        if len(srcs)>=2 or (srcs and (hw or age<3)) or (hw and age<3):
            x["hot"]=min(9,len(srcs)*2+(2 if hw else 0)+(1 if age<2 else 0)+1)
def mix(L):
    g={}
    for x in L: g.setdefault(x["source"],[]).append(x)
    q=list(g.values()); o=[]; i=0
    while len(o)<len(L):
        for a in q:
            if i<len(a): o.append(a[i])
        i+=1
    return o
HOTN=4
def order(L):
    H=sorted([x for x in L if x.get("hot")],key=lambda x:(-x["hot"],-int(x["time"])))[:HOTN]; hs={x["id"] for x in H}
    return H+mix([x for x in L if x["id"] not in hs])
def playlists(items):
    L=[items]+[[x for x in items if x["channel"]==c] for c in sorted({x["channel"] for x in items})]
    L+=[[x for x in items if x["channel"]==c and x.get("sub")==s] for c,s in sorted({(x["channel"],x.get("sub")) for x in items if x.get("sub")})]
    L+=[[x for x in items if x["channel"]=="bat-dong-san" and x.get("city")==cy] for cy in sorted({x.get("city") for x in items if x["channel"]=="bat-dong-san" and x.get("city")})]
    return L
def wanted(items,n):
    want=[];seen=set()
    for x in sorted([x for x in items if x.get("hot")],key=lambda x:-x["hot"]):
        seen.add(x["id"]);want.append(x)
    for L in playlists(items):
        for x in order(L)[:n]:
            if x["id"] not in seen: seen.add(x["id"]); want.append(x)
    return want
