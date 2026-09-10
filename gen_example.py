#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
範例產生器：台灣各地風景 + 隨機問候語（每句 ≤15 字）。
不改正式腳本，僅用來產範例圖給使用者過目。
背景改用 photorealistic 風景照風格，標註台灣景點。
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

# 台灣各地風景（英文 prompt 給 Pollinations，中文標籤供備註）
TAIWAN_SPOTS = {
    "阿里山": "Alishan Taiwan, sea of clouds over ancient cypress forest at sunrise, misty mountain peaks, serene",
    "日月潭": "Sun Moon Lake Taiwan, tranquil alpine lake surrounded by lush green mountains, morning mist, peaceful",
    "太魯閣": "Taroko Gorge Taiwan, marble canyon walls with turquoise river below, towering cliffs, majestic",
    "台北101": "Taipei 101 skyscraper and downtown skyline at blue-hour dawn, modern city, Taiwan",
    "九份": "Jiufen old mountain town Taiwan, narrow stone lanes lined with red lanterns, misty hillside, nostalgic",
    "墾丁": "Kenting Taiwan tropical beach, white sand and turquoise sea, coconut palms, bright sunny",
    "陽明山": "Yangmingshan Taiwan, rolling green grassland with seasonal flower fields, fresh morning",
    "清水斷崖": "Qingshui Cliff Hualien Taiwan, dramatic coastal cliffs plunging into deep blue Pacific ocean",
}

# 隨機問候語池（每句 ≤15 中文字）
GREETINGS = [
    "早安，願你今天平安順心",
    "早安，今天也要加油",
    "早安，好運正在路上",
    "早安，願你心有所安",
    "早安，陽光與你同行",
    "早安，今天元氣滿滿",
    "早安，願事事皆順",
    "早安，慢活也是幸福",
    "早安，微風輕拂好心情",
    "早安，平安喜樂一整天",
    "早安，願你被溫柔以待",
    "早安，新的一天新的希望",
    "早安，笑口常開好運來",
    "早安，一切美好正發生",
    "早安，願時光溫柔待你",
]

def gen_taiwan(prompt, seed):
    full = prompt + ", photorealistic landscape photograph, natural lighting, high detail, no text, no words, no people, no animals"
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
