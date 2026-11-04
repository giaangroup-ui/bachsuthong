"""Tạo giọng chào của trợ lý Pi (edge-tts, giọng tự nhiên). Chạy: python scripts/pi_voice.py
Văn bản lấy từ pi/text.json (app hiển thị cùng văn bản)."""
import asyncio, json, os, edge_tts
V={"vi":"vi-VN-HoaiMyNeural","en":"en-US-AriaNeural","zh":"zh-CN-XiaoxiaoNeural"}
T=json.load(open("pi/text.json",encoding="utf-8"))
async def main():
    os.makedirs("pi",exist_ok=True)
    for lg,d in T.items():
        for k,txt in d.items():
            f=f"pi/{k}.{lg}.mp3"
            if os.path.exists(f): continue
            await edge_tts.Communicate(txt,V[lg],rate="+4%",pitch="+15Hz").save(f); print(f)
asyncio.run(main())
