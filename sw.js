// Cache theo phiên bản: sw.js?v=<commit>. Bản mới -> cache mới, cache cũ bị xóa. (v2: trợ lý Pi)
const V=new URL(self.location).searchParams.get("v")||"dev",P="bst-",C=P+V,SHELL=["./","./manifest.webmanifest","./icons/icon-192.png","./icons/icon-512.png"];
self.addEventListener("install",e=>{self.skipWaiting();e.waitUntil(caches.open(C).then(c=>Promise.all(SHELL.map(u=>fetch(u,{cache:"reload"}).then(r=>r.ok&&c.put(u,r)).catch(()=>{})))))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});
self.addEventListener("message",e=>{if(e.data==="skip")self.skipWaiting()});
self.addEventListener("fetch",e=>{const r=e.request,u=new URL(r.url);
 if(r.method!=="GET"||u.origin!==location.origin)return;
 if(u.pathname.includes("/data/audio/")&&u.pathname.endsWith(".mp3"))return; // âm thanh: để trình duyệt tự xử lý (Range)
 const fresh=r.mode==="navigate"||/\/$|\.html$|\.js$|\.json$|\.webmanifest$/.test(u.pathname);
 if(fresh){e.respondWith(fetch(r,{cache:"no-store"}).then(res=>{if(res.ok&&!u.pathname.endsWith("version.json")){const cp=res.clone();caches.open(C).then(c=>c.put(r.mode==="navigate"?"./":r,cp))}return res})
  .catch(()=>caches.match(r,{ignoreSearch:true}).then(m=>m||caches.match("./"))));return}
 e.respondWith(caches.match(r).then(m=>m||fetch(r).then(res=>{if(res.ok){const cp=res.clone();caches.open(C).then(c=>c.put(r,cp))}return res})))});
