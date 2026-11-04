# Dữ liệu thị trường tham khảo (miễn phí, không cần khóa) -> data/market.json
import json, time, urllib.request, re, os
from concurrent.futures import ThreadPoolExecutor
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
def get(u,t=15): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=t).read()
now=int(time.time()); F=now-45*86400
def dnse(sym,kind):
    j=json.loads(get(f"https://services.entrade.com.vn/chart-api/v2/ohlcs/{kind}?symbol={sym}&resolution=1D&from={F}&to={now}"))
    c=[float(x) for x in j["c"]]; t=j["t"]
    if len(c)<2: return None
    return dict(v=c[-1],prev=c[-2],spark=c[-22:],t=t[-1],src="DNSE")
def yahoo(sym):
    j=json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.request.quote(sym)+"?range=1mo&interval=1d"))["chart"]["result"][0]
    m=j["meta"]; c=[x for x in j["indicators"]["quote"][0]["close"] if x is not None]
    prev=m.get("chartPreviousClose") if len(c)<2 else c[-2]
    v=m.get("regularMarketPrice",c[-1])
    return dict(v=v,prev=c[-2] if len(c)>1 else prev,spark=c[-22:],t=m.get("regularMarketTime",now),src="Yahoo Finance")
IDX=[("VNINDEX","VN-Index",lambda:dnse("VNINDEX","index")),("VN30","VN30",lambda:dnse("VN30","index")),("HNX","HNX-Index",lambda:dnse("HNX","index")),("UPCOM","UPCoM",lambda:dnse("UPCOM","index")),
 ("SPX","S&P 500",lambda:yahoo("^GSPC")),("DJI","Dow Jones",lambda:yahoo("^DJI")),("IXIC","Nasdaq",lambda:yahoo("^IXIC")),("N225","Nikkei 225",lambda:yahoo("^N225")),
 ("GOLD","Vàng thế giới (USD/oz)",lambda:yahoo("GC=F")),("OIL","Dầu Brent (USD/thùng)",lambda:yahoo("BZ=F")),("BTC","Bitcoin (USD)",lambda:yahoo("BTC-USD"))]
def safe(f):
    try: return f()
    except Exception as e: return None
TICK=sorted(set("""ACB BCM BID BVH CTG FPT GAS GVR HDB HPG LPB MBB MSN MWG PLX SAB SHB SSB SSI STB TCB TPB VCB VHM VIB VIC VJC VNM VPB VRE
VIX VND HCM VCI SHS MBS FTS BSI CTS ORS AGR DIG DXG NVL KDH NLG PDR HDG KBC IDC SZC CEO DXS NTL TCH HHV VCG CII LCG HHS SCR KHG CRE TDC HQC IJC
DGC DCM DPM GMD HAH PVT PVS PVD BSR POW REE NT2 GEX GEE PC1 FRT DGW PNJ VHC ANV MSB EIB OCB NAB BAF HAG DBC VGC DPG CTD HSG NKG TCX""".split()))
out={"updated":now,"idx":[],"tk":{},"fx":None,"gold":None}
with ThreadPoolExecutor(10) as ex:
    R=list(ex.map(lambda x:safe(x[2]),IDX)); T=list(ex.map(lambda s:safe(lambda:dnse(s,"stock")),TICK))
for (k,n,_),r in zip(IDX,R):
    if r: out["idx"].append(dict(k=k,n=n,**r))
for s,r in zip(TICK,T):
    if r: out["tk"][s]=dict(v=r["v"],prev=r["prev"],spark=r["spark"][-15:],t=r["t"])
try:
    x=get("https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx").decode("utf-8","ignore")
    m=re.search(r'CurrencyCode="USD"[^>]*Buy="([\d,.]+)"[^>]*Sell="([\d,.]+)"',x)
    if m: out["fx"]=dict(buy=float(m.group(1).replace(",","")),sell=float(m.group(2).replace(",","")),src="Vietcombank",t=now)
except Exception: pass
try:
    g=[d for d in json.loads(get("https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price?zone=00"))["data"] if d["masp"]=="SJC"][0]
    out["gold"]=dict(buy=g["giamua"]*10/1000,sell=g["giaban"]*10/1000,src="PNJ niêm yết",t=now)  # triệu đồng/lượng
except Exception: pass
os.makedirs("data",exist_ok=True); json.dump(out,open("data/market.json","w"),ensure_ascii=False)
print("market:",[i["k"] for i in out["idx"]],"tickers",len(out["tk"]),"/",len(TICK),"fx",bool(out["fx"]),"gold",out["gold"])
