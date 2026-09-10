#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成每日 LINE 早安圖（正式版）：
  1) 抓台北當天天氣（Open-Meteo 免 key），用於顯示天氣/降雨機率
  2) 背景：隨機挑一台灣白天風景（photorealistic 風景照風格，避夜景）
  3) 問候語：從 135 句池（≤45 字，網路問候語大全）隨機抽一句
  4) 用楷書疊上中文「早安」+ 台北日期 + 天氣 + 隨機問候語 + 節氣（直式行書雙線框紅印章）
  5) 失敗時 fallback 到漸層底圖，保證每天都有圖可推
輸出： output/goodmorning_YYYYMMDD_HHMMSS.png
"""
import os, sys, io, datetime, random

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(BASE, "output")
os.makedirs(OUTDIR, exist_ok=True)

SIZE = (1024, 1024)
FONT_NOTO_TC = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"  # NAS 上 Noto CJK TC（備用）
FONT_KAI = "/usr/share/fonts/truetype/ukai/ukai.ttc"  # NAS 上楷書（AR PL UKai TW）
FONT_XING = "/usr/share/fonts/truetype/mashan/mashan.ttf"  # NAS 上 行書（Ma Shan Zheng）

# ---- 天氣情境主題池（依 WMO weather_code 選情境，用於「天氣標籤/字串」）----
WEATHER_THEMES = {
    "clear":   {"label": "晴"},
    "cloudy":  {"label": "多雲"},
    "fog":     {"label": "霧"},
    "rain":    {"label": "雨"},
    "drizzle": {"label": "毛毛雨"},
    "snow":    {"label": "雪"},
    "thunder": {"label": "雷陣雨"},
    "wind":    {"label": "風"},
}

def weather_bucket(code, precip_prob):
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "clear" if (precip_prob or 0) < 20 else "cloudy"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "thunder"
    return "cloudy"

# ---- 台灣白天風景池（英文名給 Pollinations，中文標籤備註；盡量避免夜景）----
# 已剔除 AI 不易畫準的太魯閣（變綠色植被峽谷）、合歡山（變富士山）。
# 新增易生成的台灣景點（花東縱谷/澎湖藍灣/金針花海/溪頭竹林/台東日出）。
TAIWAN_SPOTS = {
    "台北101":   "Taipei 101 skyscraper and downtown skyline at bright daytime blue sky, modern city Taiwan, sunny",
    "日月潭":     "Sun Moon Lake Taiwan, tranquil alpine lake surrounded by lush green mountains, daytime, peaceful",
    "墾丁":       "Kenting Taiwan tropical beach, white sand and turquoise sea, coconut palms, bright sunny daytime",
    "九份":       "Jiufen old mountain town Taiwan, narrow stone lanes lined with red lanterns, misty hillside daytime, nostalgic",
    "陽明山":     "Yangmingshan Taiwan, rolling green grassland with seasonal flower fields, fresh morning daytime",
    "清水斷崖":   "Qingshui Cliff Hualien Taiwan, dramatic coastal cliffs plunging into deep blue Pacific ocean, daytime",
    "阿里山":     "Alishan Taiwan, sea of clouds over ancient cypress forest at sunrise, misty mountain peaks, serene daytime",
    "野柳":       "Yehliu Taiwan, weird rock formations (queen head) on coastline, blue ocean behind, bright daytime",
    "花蓮鯉魚潭": "Liyu Lake Hualien Taiwan, calm mountain lake with reflections, green hills around, sunny daytime",
    "十分瀑布":   "Shifen Waterfall Taiwan, broad waterfall in green forest, misty, bright daytime nature",
    "茶山梯田":   "Taiwan tea terraces hillside, neat green tea rows on slope, morning mist, serene daytime",
    "東北角海岸": "Northeast coast Taiwan, rocky shoreline with blue sea waves, green headlands, sunny daytime",
    "嘉明湖":     "Jiaming Lake Taiwan, high mountain alpine lake with turquoise water, surrounded by peaks, daytime",
    "雪霸山脈":   "Xueshan mountain range Taiwan, rugged peaks above cloud sea, golden sunrise light, daytime majestic",
    "花東縱谷":   "Huadong Valley Taiwan, green agricultural valley between two mountain ranges, rice paddies and farmland, bright daytime",
    "澎湖藍灣":   "Penghu Taiwan, turquoise blue bay with basalt coastline, clear shallow water, sunny daytime",
    "金針花海":   "Taiwan daylily flower sea, golden orange flowers covering green hills, summer bloom, bright daytime",
    "溪頭竹林":   "Xitou Taiwan bamboo forest, tall green bamboo grove with sunlight filtering, peaceful daytime",
    "台東日出":   "Taitung Taiwan east coast, golden sunrise over the Pacific ocean, first sunrise of Taiwan, bright",
}

# ---- 隨機問候語池（≤45 字，來源：網路早安問候語大全；已排除廣告句/emoji）----
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

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

# 24 節氣（21 世紀公式用）： (名稱, 月份, C 常數)
SOLAR_TERMS = [
    ("小寒", 1, 5.4055), ("大寒", 1, 20.12),
    ("立春", 2, 3.87), ("雨水", 2, 18.73),
    ("驚蟄", 3, 5.63), ("春分", 3, 20.646),
    ("清明", 4, 4.81), ("穀雨", 4, 20.1),
    ("立夏", 5, 5.52), ("小滿", 5, 21.04),
    ("芒種", 6, 5.678), ("夏至", 6, 21.37),
    ("小暑", 7, 7.108), ("大暑", 7, 22.83),
    ("立秋", 8, 7.5), ("處暑", 8, 23.13),
    ("白露", 9, 7.646), ("秋分", 9, 23.042),
    ("寒露", 10, 8.318), ("霜降", 10, 23.438),
    ("立冬", 11, 7.438), ("小雪", 11, 22.36),
    ("大雪", 12, 7.18), ("冬至", 12, 21.94),
]

def get_solar_term(d):
    Y = d.year % 100
    L = (Y - 1) // 4
    for name, month, C in SOLAR_TERMS:
        day = int(Y * 0.2422 + C) - L
        if d.month == month and d.day == day:
            return name
    return None

def taipei_now():
    return datetime.datetime.now()

def get_weather():
    try:
        url = ("https://api.open-meteo.com/v1/forecast"
               "?latitude=25.03&longitude=121.56"
               "&current=temperature_2m,weather_code,precipitation_probability"
               "&timezone=Asia%2FTaipei")
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            c = r.json().get("current", {})
            code = c.get("weather_code")
            temp = c.get("temperature_2m")
            precip = c.get("precipitation_probability")
            bucket = weather_bucket(code, precip or 0)
            return {"bucket": bucket, "code": code, "temp": temp, "precip": precip,
                    "label": WEATHER_THEMES[bucket]["label"]}
    except Exception as e:
        print(f"  [weather] 取得失敗: {e}", file=sys.stderr)
    return None

def load_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_KAI, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_NOTO_TC, size)
        except Exception:
            return ImageFont.load_default()

BG_DIR = os.path.join(BASE, "backgrounds")
CREDIT_FILE = os.path.join(BG_DIR, "credits.tsv")

def load_credits():
    """讀取 backgrounds/credits.tsv -> {檔名: 作者}"""
    credits = {}
    if os.path.exists(CREDIT_FILE):
        import csv
        with open(CREDIT_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                credits[row.get("file", "")] = row.get("photographer", "")
    return credits

def pick_local_background():
    """從 backgrounds/ 隨機挑一張真實台灣風景照當底圖，回傳 (img, credit_str)。"""
    if os.path.isdir(BG_DIR):
        files = [f for f in os.listdir(BG_DIR)
                 if f.lower().endswith((".jpg", ".jpeg", ".png"))
                 and not f.startswith(".")]
        if files:
            fname = random.choice(files)
            path = os.path.join(BG_DIR, fname)
            try:
                img = Image.open(path).convert("RGB")
                w, h = img.size
                side = min(w, h)
                top = max(0, h - side - int(side * 0.05))
                left = (w - side) // 2
                img = img.crop((left, top, left + side, top + side))
                img = img.resize(SIZE, Image.LANCZOS)
                author = load_credits().get(fname, "")
                credit = f"Photo: {author} on Pexels" if author else "Photo: Pexels"
                return img, credit
            except Exception as e:
                print(f"  [bg] 讀取 {path} 失敗: {e}", file=sys.stderr)
    return None, ""

def gen_taiwan_background(prompt, seed):
    full = prompt + ", photorealistic landscape photograph, natural daylight, high detail, no text, no words, no people, no animals"
    url = ("https://image.pollinations.ai/prompt/"
           + requests.utils.quote(full)
           + f"?width={SIZE[0]}&height={SIZE[1]}&nologo=true&model=flux&seed={seed}")
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and r.content[:2] in (b"\xff\xd8", b"\x89P"):
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                return img.resize(SIZE, Image.LANCZOS)
        except Exception as e:
            print(f"  [ai] attempt {attempt+1} failed: {e}", file=sys.stderr)
    return None

def fallback_background(seed, bucket="cloudy"):
    random.seed(seed)
    img = Image.new("RGB", SIZE, (0, 0, 0))
    d = ImageDraw.Draw(img)
    palettes = {
        "clear": ((255, 213, 150), (255, 244, 224)),
        "rain": ((150, 170, 190), (225, 232, 238)),
        "snow": ((220, 230, 240), (245, 248, 252)),
        "fog": ((200, 210, 205), (235, 240, 235)),
        "thunder": ((90, 95, 120), (180, 185, 205)),
    }
    top, bot = palettes.get(bucket, ((255, 214, 165), (255, 245, 230)))
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        c = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
        d.line([(0, y), (SIZE[0], y)], fill=c)
    if bucket in ("clear", "wind"):
        d.ellipse([SIZE[0] * 0.62, SIZE[1] * 0.12, SIZE[0] * 0.82, SIZE[1] * 0.32], fill=(255, 238, 200))
    return img

def add_text(img, date_str, weekday, weather_str, greeting, term=None, credit=""):
    d = ImageDraw.Draw(img)

    f_big = load_font(120)
    f_date = load_font(50)
    f_weather = load_font(44)
    f_small = load_font(42)

    # 左上角節氣：直式書寫（行書字體）+ 雙線框 + 紅色印章
    if term:
        try:
            f_term = ImageFont.truetype(FONT_XING, 90)
        except Exception:
            f_term = load_font(90)
        chars = list(term)  # 每字一行，由上往下
        lh = 100  # 行高
        box_x = 36
        box_y = 36
        box_w = 120
        box_h = lh * len(chars) + 40
        # 雙線框
        d.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], outline=(255, 255, 255), width=3)
        d.rectangle([box_x + 8, box_y + 8, box_x + box_w - 8, box_y + box_h - 8], outline=(255, 255, 255), width=1)
        # 直式文字（白字）
        for i, ch in enumerate(chars):
            cb = d.textbbox((0, 0), ch, font=f_term)
            cx = box_x + (box_w - (cb[2] - cb[0])) // 2
            d.text((cx, box_y + 20 + i * lh), ch, font=f_term, fill="white")
        # 紅色印章（右下角小方塊）
        seal_x = box_x + box_w - 34
        seal_y = box_y + box_h - 6
        d.rectangle([seal_x, seal_y - 34, seal_x + 34, seal_y], fill=(200, 30, 30))
        d.text((seal_x + 4, seal_y - 32), "節", font=load_font(26), fill="white")

    # 出處小字（右下角，透明背景，小一號白字）
    if credit:
        try:
            f_credit = ImageFont.truetype(FONT_KAI, 20)
        except Exception:
            f_credit = load_font(20)
        cb = d.textbbox((0, 0), credit, font=f_credit)
        cw = cb[2] - cb[0]
        ch = cb[3] - cb[1]
        cx = SIZE[0] - cw - 20
        cy = SIZE[1] - ch - 14
        # 無背景（透明）；純白字，淺灰陰影增加可讀性
        d.text((cx + 1, cy + 1), credit, font=f_credit, fill=(80, 80, 80))
        d.text((cx, cy), credit, font=f_credit, fill=(255, 255, 255, 210))

    # 文字直接貼在風景圖上（無灰色遮罩）
    base_y = SIZE[1] - 400

    # 第一行：早安
    big = "早安"
    bb = d.textbbox((0, 0), big, font=f_big)
    bx = (SIZE[0] - (bb[2] - bb[0])) // 2
    d.text((bx, base_y), big, font=f_big, fill="white")

    # 第二行：日期 星期
    date_line = f"{date_str} {weekday}"
    db = d.textbbox((0, 0), date_line, font=f_date)
    dx = (SIZE[0] - (db[2] - db[0])) // 2
    d.text((dx, base_y + 150), date_line, font=f_date, fill="white")

    # 第三行：天氣 + 降雨機率
    wb = d.textbbox((0, 0), weather_str, font=f_weather)
    wx = (SIZE[0] - (wb[2] - wb[0])) // 2
    d.text((wx, base_y + 222), weather_str, font=f_weather, fill="white")

    # 第四行：問候語
    gb = d.textbbox((0, 0), greeting, font=f_small)
    gx = (SIZE[0] - (gb[2] - gb[0])) // 2
    d.text((gx, base_y + 300), greeting, font=f_small, fill="white")
    return img

def main():
    now = taipei_now()
    seed = now.year * 10000 + now.month * 100 + now.day
    random.seed(seed)  # 每天穩定但不同天不同
    date_str = f"{now.year}年{now.month}月{now.day}日"
    weekday = WEEKDAYS[now.weekday()]
    term = get_solar_term(now)

    w = get_weather()
    if w:
        bucket = w["bucket"]
        wlabel = w["label"]
        temp = w.get("temp")
        precip = w.get("precip")
        precip_int = int(round(precip)) if precip is not None else None
        weather_str = f"{wlabel} {int(round(temp))}°C 降雨機率{precip_int}％" if precip_int is not None else f"{wlabel} {int(round(temp))}°C"
        print(f"[gen] {date_str} {weekday} | 天氣={wlabel} {temp}°C 降雨{precip}% -> {bucket}")
    else:
        print("[gen] 天氣取得失敗，用多雲預設", file=sys.stderr)
        bucket = "cloudy"
        weather_str = ""

    # 背景：優先隨機挑一張本地真實台灣風景照；若無則退回 AI 生成
    bg, credit = pick_local_background()
    if bg is not None:
        print(f"[gen] 使用本地台灣風景照當底圖 | {credit}")
    else:
        spot_label, spot_prompt = random.choice(list(TAIWAN_SPOTS.items()))
        bg = gen_taiwan_background(spot_prompt, seed)
        if bg is None:
            print("[gen] AI 底圖失敗，使用 fallback 漸層圖", file=sys.stderr)
            bg = fallback_background(seed, bucket)
        else:
            print(f"[gen] AI 底圖取得成功（{spot_label}）")

    # 問候語：隨機抽一句（≤45 字）
    greeting = random.choice(GREETINGS)

    img = add_text(bg, date_str, weekday, weather_str, greeting, term=term, credit=credit)
    if term:
        print(f"[gen] 今日節氣: {term}")
    print(f"[gen] 問候語: {greeting}")
    out = os.path.join(OUTDIR, f"goodmorning_{now.strftime('%Y%m%d_%H%M%S')}.png")
    img.save(out)
    print(f"[gen] 已儲存: {out}")
    thumb = img.copy()
    thumb.thumbnail((360, 360))
    tpath = os.path.join(OUTDIR, "latest_thumb.png")
    thumb.save(tpath)
    print(f"[gen] 預覽縮圖: {tpath}")
    return out

if __name__ == "__main__":
    main()
