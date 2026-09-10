#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
範例產生器 v2：台灣白天風景（大池、避夜景） + 隨機問候語（≤45字，取自網路問候語大全）。
不改正式腳本，僅產範例圖供使用者過目。
"""
import os, sys, io, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_goodmorning as G
import requests
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output_examples")
os.makedirs(OUT, exist_ok=True)
SIZE = (1024, 1024)

# 台灣各地白天風景（英文 prompt 給 Pollinations，中文標籤備註）。儘量避免夜景。
TAIWAN_SPOTS = {
    "台北101": "Taipei 101 skyscraper and downtown skyline at bright daytime blue sky, modern city Taiwan, sunny",
    "日月潭": "Sun Moon Lake Taiwan, tranquil alpine lake surrounded by lush green mountains, daytime, peaceful",
    "太魯閣": "Taroko Gorge Taiwan, marble canyon walls with turquoise river below, towering cliffs, daytime majestic",
    "墾丁": "Kenting Taiwan tropical beach, white sand and turquoise sea, coconut palms, bright sunny daytime",
    "九份": "Jiufen old mountain town Taiwan, narrow stone lanes lined with red lanterns, misty hillside daytime, nostalgic",
    "陽明山": "Yangmingshan Taiwan, rolling green grassland with seasonal flower fields, fresh morning daytime",
    "清水斷崖": "Qingshui Cliff Hualien Taiwan, dramatic coastal cliffs plunging into deep blue Pacific ocean, daytime",
    "阿里山": "Alishan Taiwan, sea of clouds over ancient cypress forest at sunrise, misty mountain peaks, serene daytime",
    "合歡山": "Hehuanshan Taiwan, high mountain grassland with rolling hills and sea of clouds, clear blue sky daytime",
    "野柳": "Yehliu Taiwan, weird rock formations (queen head) on coastline, blue ocean behind, bright daytime",
    "花蓮鯉魚潭": "Liyu Lake Hualien Taiwan, calm mountain lake with reflections, green hills around, sunny daytime",
    "十分瀑布": "Shifen Waterfall Taiwan, broad waterfall in green forest, misty, bright daytime nature",
    "茶山梯田": "Taiwan tea terraces hillside, neat green tea rows on slope, morning mist, serene daytime",
    "東北角海岸": "Northeast coast Taiwan, rocky shoreline with blue sea waves, green headlands, sunny daytime",
    "嘉明湖": "Jiaming Lake Taiwan, high mountain alpine lake with turquoise water, surrounded by peaks, daytime",
    "雪霸山脈": "Xueshan mountain range Taiwan, rugged peaks above cloud sea, golden sunrise light, daytime majestic",
}

# 隨機問候語池（≤45 字，來源：網路早安問候語大全；已排除廣告句）
GREETINGS = [
    "早安！希望你今天的每一刻都充滿陽光與好心情！",
    "早上好！願你今天順順利利，一切都心想事成！",
    "早安！願今天的陽光為你帶來滿滿的能量！",
    "早上好，願你的生活像陽光一樣燦爛！",
    "早晨的清風是最好的祝福，願它帶給你一天的好運！",
    "早安！新的一天，新的目標，讓我們一起努力！",
    "美好的早晨，送上滿滿的祝福，願你今天心情愉快！",
    "早安！一切從早晨開始，祝福你成功開啟好運模式！",
    "早安，別忘了用微笑迎接今天的每個時刻！",
    "早上好，喝杯茶放輕鬆，祝福你元氣滿滿！",
    "美好的一天從早晨開始，祝你充滿活力與快樂！",
    "早晨的陽光溫暖心房，祝你幸福快樂每一天！",
    "早安！迎接新挑戰，願你開心過每一分每一秒！",
    "早上好，願你的笑容像陽光一樣燦爛，驅散陰霾！",
    "早安！把握今天，讓幸福充滿你的每一天！",
    "早上好，願你的生活甜蜜如蜂蜜，幸福每一天！",
    "早安！開始美好的一天，祝福你快樂無比！",
    "早上好！願你今天像春天的花朵一樣燦爛！",
    "早安！記得用正能量迎接今天的每個挑戰！",
    "早安！希望你的心情像天空一樣晴朗！",
    "早上好！新的一天讓我們一起邁向成功！",
    "早安！願你今天充滿自信，迎接每個挑戰！",
    "美好的早晨開始了，願你每天都像今天一樣幸福！",
    "早晨好！願你的生活像彩虹般多姿多彩！",
    "早上好！帶著笑容出門，讓快樂陪伴你一整天！",
    "新的一天，祝福你工作順利，生活愉快！",
    "早安！願你今天的每分每秒都充滿美好的驚喜！",
    "早上好！別忘了給自己一個大大的微笑！",
    "早安！今天又是全新的一天，加油吧！",
    "清晨的陽光是最好的祝福，送給正在努力的你！",
    "早上好！讓今天的每一刻都變得更有意義！",
    "美好的清晨，願你的日子越來越美滿！",
    "早安！希望你今天好運連連，事事如意！",
    "新的早晨，願你擁有滿滿的好心情！",
    "早上好！記得早餐要吃飽，才有力氣面對挑戰！",
    "早安！新的一天希望你順風順水，開心每一天！",
    "早晨好！願今天的你收穫滿滿，快樂無比！",
    "早安！願你的今天充滿好運與笑聲！",
    "早上好，喝杯茶享受美好的清晨時光！",
    "早安！希望你今天工作愉快、生活幸福！",
    "美好的早晨，願你的心情如陽光般溫暖！",
    "早上好！讓我們一起迎接這美好的一天！",
    "早安！願你用滿滿的愛心面對今天的挑戰！",
    "美好的清晨，送上我的祝福，願你一切安好！",
    "早安！希望你今天收穫滿滿的成就感！",
    "早上好！用心感受生活的美好瞬間！",
    "早安！今天的一切都會像你希望的一樣順利！",
    "早安，願你今天平安順心",
    "早晨的第一縷陽光，為你送上最溫暖的祝福！",
    "早上好！相信自己，今天也會很棒！",
    "美好的清晨，願你擁有平安與快樂！",
    "早安！願你的努力都能得到豐厚的回報！",
    "早晨好！讓我們用正能量開始今天！",
    "早安喔！每一個小進步都是值得慶祝的！",
    "早上好！希望你今天的生活充滿奇蹟！",
    "美好的清晨，送上我的祝福，願你一天順心！",
    "早安！願你每天都擁有滿滿的愛與希望！",
    "早上好！今天的挑戰就是成長的機會！",
    "早安喔！讓陽光灑滿你的心田！",
    "早晨好！願你的每一步都走得踏實與穩健！",
    "早安！努力是一種選擇，讓我們一起選擇它！",
    "新的一天，願你擁有滿滿的能量！",
    "早晨的清風輕輕吹來，帶給你我的祝福！",
    "早上好！相信美好的事情正在發生！",
    "早安！祝你今天一切順心，笑口常開！",
    "美好的早晨，願你的生活多姿多彩！",
    "早上好！相信今天的你會創造出特別的回憶！",
    "早上好！今天也要努力做最棒的自己！",
    "早安！願你今天的每一分努力都帶來好結果！",
    "美好的早晨，祝你每個夢想都能成真！",
    "早上好！每一天都值得感恩與期待！",
    "早晨好！願你今天充滿信心，開啟順利的一天！",
    "早安！感受清晨的寧靜，讓心靈更加充實！",
    "新的一天，願你擁有源源不斷的好運！",
    "早晨好！面對挑戰，記得你是最棒的！",
    "早安！願你的生活每天都有驚喜與快樂！",
    "早上好！願你的笑容像陽光一樣溫暖人心！",
    "早安！努力的每一天都會是值得珍惜的回憶！",
    "早晨的露珠閃爍著希望，祝你今天大吉大利！",
    "早安！願你的心情像花朵般美麗綻放！",
    "早上好！希望你的每一個努力都有回報！",
    "早安！每一天都是新的挑戰，願你越來越好！",
    "早晨好！祝你今天過得愉快又充實！",
    "早安！用滿滿的感恩心迎接新的一天！",
    "新的清晨，新的開始，願你充滿力量與自信！",
    "早上好！每一份付出都會成為你的成功基石！",
    "早安！讓今天的你閃耀如星光！",
    "早晨好！用心感受生活的小確幸！",
    "早安！希望你的每一天都充滿陽光與喜悅！",
    "早晨好！願你的生活像詩一樣美好！",
    "早上好！每一天都是一個新的起點，加油！",
    "早安！用一顆感恩的心去迎接所有的挑戰！",
    "新的早晨，為自己設定新目標，開啟幸福的一天！",
    "早晨好！用微笑迎接清晨的第一縷陽光！",
    "早上好！相信努力的你一定會有好結果！",
    "新的一天，願你收穫滿滿的愛與希望！",
    "早安！別忘了用溫暖的心對待自己與他人！",
    "早晨好！願你每一步都踏實，每一天都進步！",
    "早上好！希望你的今天充滿驚喜與好運！",
    "早安！願你的努力都能換來美好的果實！",
    "早晨好！享受每個當下，讓生活充滿感動！",
    "早安！希望今天的你過得充實又快樂！",
    "新的早晨，新的希望，願你勇往直前！",
    "早上好！記得每天都是值得感恩的！",
    "早安！用一顆平靜的心迎接今天的挑戰！",
    "早晨好！希望你的笑容像陽光一樣燦爛！",
    "早安！每一份真心都會換來回報！",
    "早上好！願你今天的每一刻都充滿正能量！",
    "早安！記得用微笑面對每一個困難與挑戰！",
    "早晨好！願你今天收穫滿滿的快樂與感動！",
    "早安！每一個清晨都是一個新的開始！",
    "早晨好！願你今天擁有滿滿的自信與力量！",
    "早上好！每一個小努力都會成就大夢想！",
    "早安！希望今天的你擁有無比的幸福與美好！",
    "新的一天，願你用心經營屬於自己的精彩生活！",
    "早晨好！帶著希望上路，祝福你一路順風！",
    "早安！願你的每一個選擇都能帶來好結果！",
    "美好的清晨，願你的生活充滿陽光與溫暖！",
    "早晨好！讓我們用滿滿的期待迎接今天！",
    "早上好！希望你今天的心情像春天一樣美麗！",
    "早安！願你的生活每天都像今天一樣精彩！",
    "早晨好！用努力為自己打造一個更美好的未來！",
    "早安！希望你的笑容像陽光一樣溫暖人心！",
    "早上好！願你今天的每一刻都充滿感恩與喜悅！",
    "早晨好！為自己的夢想全力以赴吧！",
    "早安！今天又是讓人充滿希望的一天！",
    "美好的清晨，願你擁有滿滿的愛與幸福！",
    "新的一天，願你的努力帶來無限的可能性！",
    "早晨好！每一份堅持都會讓你更接近成功！",
    "早安！今天是讓自己變得更好的機會！",
    "早上好！願你今天的每一刻都充滿幸福與快樂！",
    "早晨好！祝福你今天一切順心如意！",
    "早安！希望你擁有一個無憂無慮的美好一天！",
    "新的一天，願你擁有滿滿的勇氣與力量！",
    "早晨好！每一份努力都會讓你更接近幸福！",
    "早安！願你今天的每一刻都充滿美好的驚喜！",
    "早晨好！讓我們用堅持與努力迎接未來！",
    "新的一天，願你的生活越來越美滿幸福！",
    "早上好！希望你今天的生活充滿陽光與笑聲！",
    "早安！願你的每一天都比昨天更好！",
    "早晨好！願你的今天比昨天更加燦爛！",
    "早安！希望你的生活每天都充滿溫暖與愛！",
    "早上好！每一個新的早晨都是一個新的起點！",
    "新的一天開始了，願你擁有滿滿的快樂與能量！",
    "早晨好！用正能量面對一切挑戰與機會！",
    "早安！願你的生活像春天的花朵般多彩！",
    "早上好！記得用感恩的心迎接今天的一切！",
    "新的一天，願你用笑容點亮每一個瞬間！",
    "早晨好！希望你的生活每天都更加幸福與美好！",
    "早安喔！今天又是一個值得期待的美好日子！",
    "美好的清晨，願你今天收穫滿滿的愛與快樂！",
    "早安！新的一天，記得好好照顧自己！",
    "早上好！希望今天的陽光溫暖你的心！",
    "早安！為今天的每一刻感到驕傲吧！",
    "早晨好！努力的你永遠不會被辜負！",
    "早上好！每一天都是新的希望！",
    "早安！珍惜眼前人，擁抱每個微笑！",
    "早晨好！祝福你今天平安順遂！",
    "新的一天，願你勇敢追夢！",
    "早上好！用一杯熱茶溫暖自己的清晨！",
    "早安！今天一定是個特別的日子！",
]

def gen_taiwan(prompt, seed):
    full = prompt + ", photorealistic landscape photograph, natural daylight, high detail, no text, no words, no people, no animals"
    url = ("https://image.pollinations.ai/prompt/" + requests.utils.quote(full)
           + f"?width={SIZE[0]}&height={SIZE[1]}&nologo=true&model=flux&seed={seed}")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and r.content[:2] in (b"\xff\xd8", b"\x89P"):
                return Image.open(io.BytesIO(r.content)).convert("RGB").resize(SIZE, Image.LANCZOS)
        except Exception as e:
            print("  attempt", attempt + 1, "failed:", e, file=sys.stderr)
    return None

now = G.taipei_now()
date_str = f"{now.year}年{now.month}月{now.day}日"
weekday = G.WEEKDAYS[now.weekday()]
term = G.get_solar_term(now)

w = G.get_weather()
if w:
    precip_int = int(round(w.get("precip") or 0))
    weather_str = f"{w['label']} {int(round(w['temp']))}°C 降雨機率{precip_int}％" if precip_int is not None else f"{w['label']} {int(round(w['temp']))}°C"
else:
    weather_str = ""

items = list(TAIWAN_SPOTS.items())
random.seed()
picks = random.sample(items, min(4, len(items)))

summary = []
for i, (label, prompt) in enumerate(picks):
    seed = (now.year * 10000 + now.month * 100 + now.day) * 100 + i * 7 + 3
    bg = gen_taiwan(prompt, seed)
    if bg is None:
        print(f"  [{label}] AI 底圖失敗，用 fallback", file=sys.stderr)
        bg = G.fallback_background(seed, "clear")
    greeting = random.choice(GREETINGS)
    img = G.add_text(bg, date_str, weekday, weather_str, greeting, term=term)
    out = os.path.join(OUT, f"example_{i+1}_{label}.png")
    img.save(out)
    print("SAVED", out, "| spot:", label, "| greeting:", greeting)
    summary.append((label, greeting, out))

with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as f:
    for label, g, p in summary:
        f.write(f"{label}\t{g}\t{p}\n")
print("DONE", len(summary), "examples")
