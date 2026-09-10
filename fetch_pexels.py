#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 Pexels 官方 API 抓取台灣風景照，存入 backgrounds/ 並記錄作者資訊（credits.tsv）。
僅下載、不下疊文字；每日早安圖腳本會從 backgrounds/ 隨機挑一張當底圖。
"""
import os, sys, json, time, csv
import requests
from PIL import Image
from io import BytesIO

BASE = os.path.dirname(os.path.abspath(__file__))
BG_DIR = os.path.join(BASE, "backgrounds")
os.makedirs(BG_DIR, exist_ok=True)
TOKEN_FILE = os.path.join(BASE, ".pexels_token")
CREDIT_FILE = os.path.join(BG_DIR, "credits.tsv")

# 每個景點：搜尋關鍵字 + 預期地點（供 vision 驗證用，僅註解）
SPOTS = {
    "taroko":   ("taroko gorge taiwan marble canyon", "太魯閣大理石峽谷"),
    "hehuan":   ("hehuanshan taiwan sea of clouds",   "合歡山雲海高山草原"),
    "huadong":  ("hualien valley taiwan rice field",  "花東縱谷田野"),
    "penghu":   ("penghu taiwan blue bay",            "澎湖藍灣"),
    "daylily":  ("taiwan daylily flower hill",        "金針花海"),
    "xitou":    ("xitou bamboo forest taiwan",        "溪頭竹林"),
    "taitung":  ("taitung taiwan sunrise pacific",    "台東太平洋日出"),
    "sunmoon":  ("sun moon lake taiwan",              "日月潭"),
    "alishan":  ("alishan taiwan cloud sea",          "阿里山雲海"),
    "kenting":  ("kenting taiwan beach",              "墾丁海灘"),
    "jiufen":   ("jiufen taiwan old town",            "九份山城"),
    "yangmingshan": ("yangmingshan taiwan",           "陽明山"),
}

def load_token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()

def search(token, query, per_page=10):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": token}
    params = {"query": query, "per_page": per_page, "locale": "zh-TW"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code == 200:
        return r.json().get("photos", [])
    print(f"  [search] {query} 失敗 HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
    return []

def main():
    token = load_token()
    # 讀取已存在的 credits（避免重複下載同一張）
    existing = {}
    if os.path.exists(CREDIT_FILE):
        with open(CREDIT_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                existing[row["photo_id"]] = row
    credits = list(existing.values())
    new_count = 0
    for key, (query, label) in SPOTS.items():
        print(f"[抓取] {key} ({label}) query={query}")
        photos = search(token, query, per_page=8)
        for p in photos:
            pid = str(p["id"])
            if pid in existing:
                continue
            # 取較大尺寸但可控（1024~1280 寬），避免原圖過大
            src = p["src"].get("large") or p["src"].get("large2x") or p["src"]["original"]
            try:
                r = requests.get(src, timeout=60)
                if r.status_code != 200:
                    continue
                img = Image.open(BytesIO(r.content)).convert("RGB")
                # 存檔：taiwan_<spot>_<id>.jpeg
                fname = f"taiwan_{key}_{pid}.jpeg"
                img.save(os.path.join(BG_DIR, fname), "JPEG", quality=88)
                credits.append({
                    "photo_id": pid,
                    "file": fname,
                    "spot": key,
                    "label": label,
                    "photographer": p.get("photographer", ""),
                    "photographer_url": p.get("photographer_url", ""),
                    "pexels_url": p.get("url", ""),
                })
                existing[pid] = credits[-1]
                new_count += 1
                print(f"  下載 {fname} (by {p.get('photographer')})")
            except Exception as e:
                print(f"  下載 {pid} 失敗: {e}", file=sys.stderr)
            time.sleep(0.3)  # 避免觸發 rate limit
        time.sleep(1)
    # 寫回 credits.tsv
    with open(CREDIT_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["photo_id", "file", "spot", "label",
                                          "photographer", "photographer_url", "pexels_url"],
                           delimiter="\t")
        w.writeheader()
        for c in credits:
            w.writerow(c)
    print(f"\n[完成] 新增 {new_count} 張，總計 {len(credits)} 張；credit 寫入 {CREDIT_FILE}")

if __name__ == "__main__":
    main()
