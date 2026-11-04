# Dịch tiêu đề/tóm tắt/bài viết sang vi/en/zh và tạo giọng đọc MC (edge-tts). Có cache trong cache/.
import json, os, re, time, asyncio, urllib.request, urllib.parse, shutil
LANGS=["vi","en","zh"]; GT={"vi":"vi","en":"en","zh":"zh-CN"}
VOICES={"vi":{"f":"vi-VN-HoaiMyNeural","m":"vi-VN-NamMinhNeural"},"en":{"f":"en-US-AriaNeural","m":"en-US-GuyNeural"},"zh":{"f":"zh-CN-XiaoxiaoNeural","m":"zh-CN-YunyangNeural"}}
TTS_REV="2"  # đổi khi đổi cách chuẩn hoá văn bản -> tạo lại audio
AUDIO_PER_CH=int(os.environ.get("AUDIO_PER_CH","12")); T0=time.time(); BUDGET=float(os.environ.get("BUDGET","900"))
os.makedirs("cache/audio",exist_ok=True)
if (open("cache/audio/.rev").read() if os.path.exists("cache/audio/.rev") else "")!=TTS_REV:
    shutil.rmtree("cache/audio"); os.makedirs("cache/audio"); open("cache/audio/.rev","w").write(TTS_REV)
os.makedirs("data/articles",exist_ok=True); os.makedirs("data/audio",exist_ok=True)
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
NUMW=r"(\d+(?:[.,]\d+)*)"
def clean(text,tl):
    t=re.sub(r"https?://\S+|www\.\S+|\S+@\S+\.\w+","",text)
    t=re.sub(r"[#*_~|<>\[\]{}\\^`]+"," ",t); t=re.sub(r"[\"“”«»]","",t)
    t=re.sub(r"\s*[–—]\s*",", ",t); t=re.sub(r"\.{2,}|…",". ",t)
    if tl=="vi":
        R=[(r"\bTP\.?\s?HCM\b|\bTPHCM\b","Thành phố Hồ Chí Minh"),(r"\bHN\b","Hà Nội"),(r"\bTP\.\s?","thành phố "),(r"\bUBND\b","Ủy ban nhân dân"),(r"\bBĐS\b","bất động sản"),
           (r"\bQ([1-4])/(\d{4})","quý \\1 năm \\2"),(r"(?<!ngày )\b(\d{1,2})/(\d{1,2})/(\d{4})\b","ngày \\1 tháng \\2 năm \\3"),(r"\b(\d{1,2})/(\d{4})\b","tháng \\1 năm \\2"),
           (r"(?<!ngày )\b(\d{1,2})/(\d{1,2})\b(?!/)","ngày \\1 tháng \\2"),(r"\$\s?"+NUMW,"\\1 đô la"),(NUMW+r"\s?(USD|\$)","\\1 đô la Mỹ"),(r"\bUSD\b","đô la Mỹ"),
           (NUMW+r"\s?(VNĐ|VND|đồng|đ)\b","\\1 đồng"),(r"\bVNĐ\b|\bVND\b","đồng"),(NUMW+r"\s?%","\\1 phần trăm"),(r"%"," phần trăm"),(NUMW+r"\s?(m2|m²)","\\1 mét vuông"),
           (NUMW+r"\s?(km2|km²)","\\1 ki lô mét vuông"),(NUMW+r"\s?km\b","\\1 ki lô mét"),(NUMW+r"\s?ha\b","\\1 héc ta"),(NUMW+r"\s?kg\b","\\1 ki lô gam"),
           (r"\bAI\b","Ây Ai"),(r"\bCEO\b","giám đốc điều hành"),(r"\bGDP\b","Gi Đi Pi"),(r"\bVN-?Index\b","VN Index"),(r"&"," và "),(r"\+"," cộng "),(r"\s/\s",", ")]
        for a,b in R: t=re.sub(a,b,t)
        t=re.sub(r"(?<=\d)\.(?=\d{3}\b)","",t)  # 1.000 -> 1000 để đọc đúng "một nghìn"
    else:
        t=re.sub(r"&"," and " if tl=="en" else "和",t)
    t=re.sub(r"\s*/\s*",", ",t) if tl!="vi" else t.replace("/"," ")
    t=re.sub(r"\s+([,.!?;:])",r"\1",t); t=re.sub(r"\s{2,}"," ",t).strip()
    return t
# 3) Kịch bản MC phân tích (trích xuất từ toàn văn: bối cảnh, diễn biến, số liệu, tác động, góc nhìn)
import sys, hashlib; sys.path.insert(0,os.path.dirname(__file__)); from rank import score_hot, wanted, toks
if not any(x.get("hot") for x in items): score_hot(items)
want=wanted(items,AUDIO_PER_CH)
LB={"vi":{"hot":"Tin nóng!","ctx":"Bối cảnh","main":"Diễn biến chính","num":"Số liệu đáng chú ý","imp":"Tác động và ý nghĩa","view":"Góc nhìn cho bạn"},
    "en":{"hot":"Breaking news!","ctx":"Background","main":"What happened","num":"Key figures","imp":"Impact and significance","view":"What it means for you"},
    "zh":{"hot":"热点新闻！","ctx":"背景","main":"主要进展","num":"关键数据","imp":"影响与意义","view":"给你的观察"}}
VIEW={"vi":{"tai-chinh":"Với nhà đầu tư, đây là thông tin cần theo dõi cùng diễn biến thanh khoản và dòng tiền; hãy cân nhắc kỹ khẩu vị rủi ro, tin chỉ mang tính tham khảo.","bat-dong-san":"Nếu bạn đang có kế hoạch mua nhà hay đầu tư, hãy theo dõi pháp lý, tiến độ hạ tầng và lãi vay trước khi quyết định.","ai":"Công nghệ trí tuệ nhân tạo đang thay đổi rất nhanh; đây là xu hướng đáng để bạn theo dõi và thử ứng dụng vào công việc.","van-hoa":"Một câu chuyện văn hóa giải trí thú vị, bạn có thể đọc thêm bài gốc để thưởng thức trọn vẹn.","the-gioi":"Diễn biến kinh tế thế giới có thể tác động tới giá cả, tỷ giá và thị trường trong nước, bạn nên tiếp tục theo dõi.","kinh-te-vn":"Thông tin này có thể ảnh hưởng tới doanh nghiệp và chi tiêu của mỗi gia đình, bạn nên tiếp tục theo dõi.","thoi-su":"Bạn hãy tiếp tục theo dõi Bách Sự Thông để cập nhật diễn biến mới nhất."},
 "en":{"tai-chinh":"For investors, watch this alongside market liquidity and money flows; consider your risk appetite, this is for reference only.","bat-dong-san":"If you plan to buy or invest in property, check the legal status, infrastructure progress and mortgage rates first.","ai":"AI is moving fast; this is a trend worth following and trying out in your own work.","van-hoa":"An interesting culture and entertainment story; read the original article to enjoy it in full.","the-gioi":"Global economic developments can affect prices, exchange rates and local markets, so keep an eye on it.","kinh-te-vn":"This may affect businesses and household spending, so keep following the story.","thoi-su":"Stay with Bach Su Thong for the latest updates."},
 "zh":{"tai-chinh":"对投资者而言，需结合市场流动性和资金流向关注此消息；请谨慎评估风险，仅供参考。","bat-dong-san":"如果你计划购房或投资，请先关注法律手续、基础设施进度和贷款利率。","ai":"人工智能发展迅速，这一趋势值得关注，并可尝试应用到工作中。","van-hoa":"一个有趣的文化娱乐故事，可以阅读原文完整欣赏。","the-gioi":"全球经济动态可能影响物价、汇率和国内市场，值得继续关注。","kinh-te-vn":"这可能影响企业和家庭开支，请继续关注。","thoi-su":"请继续关注百事通，获取最新动态。"}}
IMPW=re.compile(r"ảnh hưởng|tác động|dự kiến|dự báo|kỳ vọng|nhận định|cho rằng|cho biết|rủi ro|cơ hội|nhằm|giúp|impact|expect|forecast|analyst|risk|could|would|aim|said|影响|预计|预期|认为|表示|风险|机会",re.I)
DEEPC={"tai-chinh","bat-dong-san","ai","van-hoa"}
def sents(paras,tl):
    o=[]
    for p in paras or []:
        for q in re.split(r"(?<=[.!?。！？])\s*" if tl=="zh" else r"(?<=[.!?])\s+",p):
            q=q.strip()
            if (len(q)>=12 if tl=="zh" else len(q)>=40) and len(q)<(160 if tl=="zh" else 420): o.append(q)
    return o
def mc_script(x,tl,t,s,paras):
    L=LB[tl]; tt=toks(t+" "+(s or "")); S=sents(paras,tl); used=set(); deep=x["channel"] in DEEPC or x.get("hot")
    sim=lambda q:len(toks(q)&tt)
    sn=lambda q:re.sub(r"\W","",q.lower())[:50]
    if s: used.add(sn(s))
    def pick(cands,k):
        r=[]
        for i,q in cands:
            if len(r)>=k: break
            if sn(q) in used or any(len(toks(q)&toks(z))>len(toks(q))*.6 for _,z in r): continue
            used.add(sn(q)); r.append((i,q))
        return [q for i,q in sorted(r)]
    sec=[]
    sec.append(["", (L["hot"]+" " if x.get("hot") else "")+t.rstrip(".。!?！？")+("。" if tl=="zh" else ".")])
    ctx=s or (S[0] if S else "")
    if ctx: sec.append([L["ctx"],ctx]); used.add(sn(ctx))
    if S:
        idx=list(enumerate(S)); nm=3 if deep else 2
        main=pick(sorted(idx,key=lambda a:-(sim(a[1])*2+max(0,6-a[0]))),nm)
        if main: sec.append([L["main"]," ".join(main)])
        num=pick([a for a in idx if re.search(r"\d",a[1])],2 if deep else 1)
        if num: sec.append([L["num"]," ".join(num)])
        imp=pick([a for a in idx if IMPW.search(a[1])][::-1],2 if deep else 1)
        if imp: sec.append([L["imp"]," ".join(imp)])
    sec.append([L["view"],VIEW[tl].get(x["channel"],VIEW[tl]["thoi-su"])])
    return sec
ART={}
for x in want:
    if x.get("full") and os.path.exists(f"data/articles/{x['id']}.json"): ART[x["id"]]=json.load(open(f"data/articles/{x['id']}.json"))
AN={tl:{} for tl in LANGS}
for x in want:
    for tl in LANGS:
        t,s,f=loc(x,tl)
        if f==-1: continue
        AN[tl][x["id"]]=mc_script(x,tl,t,s,(ART.get(x["id"]) or {}).get(tl))
# 4) news-<lang>.json
for tl in LANGS:
    L=[]
    for x in items:
        t,s,f=loc(x,tl); y=dict(x,title=t,summary=s)
        if f==1: y["tr"]=x["lang"]
        if f==-1: y["tr"]="x"
        if x["id"] in AN[tl]: y["an"]=AN[tl][x["id"]]
        L.append(y)
    json.dump(dict(D,items=L,lang=tl),open(f"data/news-{tl}.json","w"),ensure_ascii=False)
jobs=[]
for x in want:
    for tl in LANGS:
        if x["id"] not in AN[tl]: continue
        sp=" " if tl!="zh" else ""
        text=sp.join(clean((lab+(": " if tl!="zh" else "：") if lab else "")+txt,tl) for lab,txt in AN[tl][x["id"]])
        h=hashlib.sha1(text.encode()).hexdigest()[:8]
        for g,v in VOICES[tl].items(): jobs.append((x["id"],tl,g,v,text,h))
async def tts(job,sem):
    i,tl,g,v,text,h=job; base=f"cache/audio/{i}.{tl}.{g}.{h}"
    if os.path.exists(base+".mp3") and os.path.exists(base+".json"): return base
    if time.time()-T0>BUDGET+1200: return old(i,tl,g)
    import edge_tts
    async with sem:
        for a in range(2):
            try:
                cues=[]; buf=bytearray()
                async for ch in edge_tts.Communicate(text,v,rate=("+0%" if tl=="vi" else "+3%")).stream():
                    if ch["type"]=="audio": buf+=ch["data"]
                    elif ch["type"] in("SentenceBoundary","WordBoundary"): cues.append([round(ch["offset"]/1e7,2),ch["text"]])
                if len(buf)<2000: raise Exception("short")
                open(base+".mp3","wb").write(buf); json.dump(cues,open(base+".json","w"),ensure_ascii=False); return base
            except Exception as e: await asyncio.sleep(2)
    return old(i,tl,g)
def old(i,tl,g):
    """chưa kịp tạo bản phân tích mới -> dùng bản cũ (nếu có) để không mất giọng MC"""
    c=sorted([f[:-4] for f in os.listdir("cache/audio") if f.startswith(f"{i}.{tl}.{g}") and f.endswith(".mp3") and os.path.exists("cache/audio/"+f[:-4]+".json")],key=lambda f:-os.path.getmtime("cache/audio/"+f+".mp3"))
    return "cache/audio/"+c[0] if c else False
async def run():
    sem=asyncio.Semaphore(14); return await asyncio.gather(*[tts(j,sem) for j in jobs])
res=asyncio.run(run()) if jobs else []
keep=set(); IDX={tl:{} for tl in LANGS}
for f in os.listdir("data/audio"):
    if f.endswith(".mp3"): os.remove("data/audio/"+f)
for j,ok in zip(jobs,res):
    if not ok: continue
    i,tl,g=j[:3]; keep.add(os.path.basename(ok))
    shutil.copy(ok+".mp3",f"data/audio/{i}.{tl}.{g}.mp3")
    IDX[tl].setdefault(i,{})[g]=json.load(open(ok+".json"))
for f in os.listdir("cache/audio"):
    if f!=".rev" and f.rsplit(".",1)[0] not in keep: os.remove("cache/audio/"+f)
for tl in LANGS: json.dump(IDX[tl],open(f"data/audio/{tl}.json","w"),ensure_ascii=False)
size=sum(os.path.getsize("data/audio/"+f) for f in os.listdir("data/audio"))
print('hot',sum(1 for x in items if x.get('hot')),'mc scripts',len(AN['vi']));print(f"tr ok: {sum(len(v) for v in TR.values())} entries, fails={fails}; audio {sum(res)}/{len(jobs)} files, {size/1e6:.1f} MB; {time.time()-T0:.0f}s")
