# Dịch tiêu đề/tóm tắt/bài viết sang vi/en/zh và tạo giọng đọc MC (edge-tts). Có cache trong cache/.
import json, os, re, time, asyncio, urllib.request, urllib.parse, shutil
LANGS=["vi","en","zh"]; GT={"vi":"vi","en":"en","zh":"zh-CN"}
VOICES={"vi":{"f":"vi-VN-HoaiMyNeural","m":"vi-VN-NamMinhNeural"},"en":{"f":"en-US-AriaNeural","m":"en-US-GuyNeural"},"zh":{"f":"zh-CN-XiaoxiaoNeural","m":"zh-CN-YunyangNeural"}}
AUDIO_PER_CH=int(os.environ.get("AUDIO_PER_CH","12")); T0=time.time(); BUDGET=float(os.environ.get("BUDGET","900"))
os.makedirs("cache/audio",exist_ok=True); os.makedirs("data/articles",exist_ok=True); os.makedirs("data/audio",exist_ok=True)
D=json.load(open("data/news.json")); items=D["items"]
def lang_of(t): return "vi" if re.search(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]",t,re.I) else ("zh" if re.search(r"[\u4e00-\u9fff]",t) else "en")
TRF="cache/tr.json"; TR=json.load(open(TRF)) if os.path.exists(TRF) else {}
fails=0
def gt(text,tl):
    global fails
    if fails>8 or time.time()-T0>BUDGET: return None
    data=urllib.parse.urlencode({"client":"gtx","sl":"auto","tl":tl,"dt":"t","q":text}).encode()
    for a in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request("https://translate.googleapis.com/translate_a/single",data=data,headers={"User-Agent":"Mozilla/5.0","Content-Type":"application/x-www-form-urlencoded;charset=UTF-8"}),timeout=20)
            j=json.loads(r.read().decode()); time.sleep(0.25)
            return "".join(seg[0] for seg in j[0] if seg[0])
        except Exception as e:
            time.sleep(2*(a+1))
    fails+=1; return None
def tr_batch(texts,tl):
    """dịch danh sách chuỗi, gộp theo khối ~3500 ký tự, tách bằng dòng mới"""
    out=[None]*len(texts); i=0
    while i<len(texts):
        j=i; n=0
        while j<len(texts) and n+len(texts[j])<3500: n+=len(texts[j])+1; j+=1
        j=max(j,i+1); chunk=[t.replace("\n"," ") for t in texts[i:j]]
        res=gt("\n".join(chunk),tl)
        parts=res.split("\n") if res else []
        if res and len(parts)==len(chunk): out[i:j]=[p.strip() for p in parts]
        elif res:
            for k,t in enumerate(chunk): out[i+k]=gt(t,tl)
        i=j
    return out
# 1) tiêu đề + tóm tắt
for x in items: x["lang"]=lang_of(x["title"]+" "+x["summary"])
for tl in LANGS:
    todo=[x for x in items if x["lang"]!=tl and tl not in TR.get(x["id"],{})]
    if not todo: continue
    flat=[]; 
    for x in todo: flat+= [x["title"], x["summary"] or "."]
    res=tr_batch(flat,GT[tl])
    for k,x in enumerate(todo):
        t,s=res[2*k],res[2*k+1]
        if t: TR.setdefault(x["id"],{})[tl]={"t":t,"s":(s if x["summary"] else "")}
ids={x["id"] for x in items}; TR={k:v for k,v in TR.items() if k in ids}
json.dump(TR,open(TRF,"w"),ensure_ascii=False)
def loc(x,tl):
    if x["lang"]==tl: return x["title"],x["summary"],0
    v=TR.get(x["id"],{}).get(tl)
    return (v["t"],v["s"],1) if v else (x["title"],x["summary"],-1)
# 2) bài chi tiết
for x in items:
    if not x.get("full"): continue
    src=f"cache/articles/{x['id']}.json"
    if not os.path.exists(src): x.pop("full",None); continue
    a=json.load(open(src)); cf=f"cache/articles/{x['id']}.tr.json"
    trc=json.load(open(cf)) if os.path.exists(cf) else {}
    out={}
    for tl in LANGS:
        if x["lang"]==tl: out[tl]=a["paras"]; continue
        if tl not in trc:
            r=tr_batch(a["paras"],GT[tl])
            if all(r): trc[tl]=r
        out[tl]=trc.get(tl)
    json.dump(trc,open(cf,"w"),ensure_ascii=False)
    out={k:v for k,v in out.items() if v}; out["orig"]=x["lang"]
    json.dump(out,open(f"data/articles/{x['id']}.json","w"),ensure_ascii=False)
# 3) news-<lang>.json
for tl in LANGS:
    L=[]
    for x in items:
        t,s,f=loc(x,tl); y=dict(x,title=t,summary=s)
        if f==1: y["tr"]=x["lang"]
        if f==-1: y["tr"]="x"
        L.append(y)
    json.dump(dict(D,items=L,lang=tl),open(f"data/news-{tl}.json","w"),ensure_ascii=False)
# 4) giọng đọc cho danh sách phát TV (khớp hàm mix() phía trình duyệt)
def mix(L):
    g={}
    for x in L: g.setdefault(x["source"],[]).append(x)
    q=list(g.values()); o=[]; i=0
    while len(o)<len(L):
        for a in q:
            if i<len(a): o.append(a[i])
        i+=1
    return o
chans=[None]+sorted({x["channel"] for x in items})
want=[]
for c in chans:
    for x in mix([x for x in items if c is None or x["channel"]==c])[:AUDIO_PER_CH]:
        if x not in want: want.append(x)
jobs=[]
for x in want:
    for tl in LANGS:
        t,s,f=loc(x,tl)
        if f==-1: continue
        text=t.rstrip(".。!?！？")+". "+(s or "").rstrip("…")
        for g,v in VOICES[tl].items(): jobs.append((x["id"],tl,g,v,text))
async def tts(job,sem):
    i,tl,g,v,text=job; base=f"cache/audio/{i}.{tl}.{g}"
    if os.path.exists(base+".mp3") and os.path.exists(base+".json"): return True
    if time.time()-T0>BUDGET+300: return False
    import edge_tts
    async with sem:
        for a in range(2):
            try:
                cues=[]; buf=bytearray()
                async for ch in edge_tts.Communicate(text,v,rate="+5%").stream():
                    if ch["type"]=="audio": buf+=ch["data"]
                    elif ch["type"] in("SentenceBoundary","WordBoundary"): cues.append([round(ch["offset"]/1e7,2),ch["text"]])
                if len(buf)<2000: raise Exception("short")
                open(base+".mp3","wb").write(buf); json.dump(cues,open(base+".json","w"),ensure_ascii=False); return True
            except Exception as e: await asyncio.sleep(2)
    return False
async def run():
    sem=asyncio.Semaphore(6); return await asyncio.gather(*[tts(j,sem) for j in jobs])
res=asyncio.run(run()) if jobs else []
keep=set(); IDX={tl:{} for tl in LANGS}
for j,ok in zip(jobs,res):
    if not ok: continue
    i,tl,g,v,_=j; base=f"{i}.{tl}.{g}"; keep.add(base)
    shutil.copy(f"cache/audio/{base}.mp3",f"data/audio/{base}.mp3")
    IDX[tl].setdefault(i,{})[g]=json.load(open(f"cache/audio/{base}.json"))
for f in os.listdir("cache/audio"):
    if f.rsplit(".",1)[0] not in keep: os.remove("cache/audio/"+f)
for tl in LANGS: json.dump(IDX[tl],open(f"data/audio/{tl}.json","w"),ensure_ascii=False)
size=sum(os.path.getsize("data/audio/"+f) for f in os.listdir("data/audio"))
print(f"tr ok: {sum(len(v) for v in TR.values())} entries, fails={fails}; audio {sum(res)}/{len(jobs)} files, {size/1e6:.1f} MB; {time.time()-T0:.0f}s")
