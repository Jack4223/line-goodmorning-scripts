#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
上傳早安圖到 GitHub (Jack4223/iptv-m3u 的 goodmorning/ 目錄)，
並回傳 raw.githubusercontent.com 的公開網址，供 LINE push image 使用。

圖床來源選 GitHub raw 的原因：
  - 免 key、免費、永久可連（raw.githubusercontent 是穩定 CDN）
  - 沿用既有的 fine-grained PAT（範圍僅 iptv-m3u），不需再申請 token
  - 每日用帶日期的檔名（goodmorning_YYYYMMDD.png）避免 CDN 快取舊圖
"""
import os, sys, json, base64, datetime
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = "Jack4223/iptv-m3u"
BRANCH = "main"
FOLDER = "goodmorning"

# 從本地隱藏檔讀 PAT（避免把 token 寫進腳本）
TOKEN_CANDIDATES = [
    os.environ.get("GITHUB_TOKEN"),
    os.path.join(BASE, ".github_token"),
    os.path.expanduser("~/.github_token"),
    r"D:\Users\Jack\OneDrive\桌面\hermes 資料夾\.github_token",
]

def load_config():
    cfg_path = os.path.join(BASE, "config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_token():
    for c in TOKEN_CANDIDATES:
        if not c:
            continue
        if os.path.isfile(c):
            with open(c, "r", encoding="utf-8") as f:
                t = f.read().strip()
                if t:
                    return t
        elif isinstance(c, str) and c.startswith("ghp_") or (c and len(c) > 30 and " " not in c and c not in TOKEN_CANDIDATES[:1] and not os.path.isfile(c)):
            return c
    return None

def github_put(path_in_repo, content_bytes, token, message):
    """PUT 到 GitHub Contents API（不存在則建立，存在則覆寫）"""
    url = f"https://api.github.com/repos/{REPO}/contents/{path_in_repo}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    # 先查是否已有（拿 sha 才能覆寫）
    sha = None
    r = requests.get(url, headers=headers, params={"ref": BRANCH}, timeout=30)
    if r.status_code == 200:
        sha = r.json().get("sha")
    b64 = base64.b64encode(content_bytes).decode("ascii")
    body = {"message": message, "content": b64, "branch": BRANCH}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=headers, json=body, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub PUT {path_in_repo} 失敗 HTTP {r.status_code}: {r.text[:300]}")
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path_in_repo}"

def upload_image(path):
    token = load_token()
    if not token:
        raise RuntimeError("找不到 GitHub PAT：請確認 .github_token 存在或設定 GITHUB_TOKEN 環境變數")
    with open(path, "rb") as fh:
        data = fh.read()
    # 用圖檔本身的檔名（含時間戳），確保每次推播都是全新 URL，避免 LINE 快取舊圖
    dated_name = os.path.basename(path)
    raw_url = github_put(f"{FOLDER}/{dated_name}", data, token,
                         f"goodmorning {dated_name}")
    print(f"[upload] 已上傳: {raw_url}")
    return raw_url

def push_to_line(token, to, image_url):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "to": to,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ],
    }
    r = requests.post("https://api.line.me/v2/bot/message/push",
                      headers=headers, json=body, timeout=30)
    print(f"[push] HTTP {r.status_code} {r.text[:200]}")
    r.raise_for_status()
    return True

def resolve_target(cfg):
    """根據 config 決定推播對象：user 模式用 user_id，group 模式用 group_id"""
    mode = cfg.get("target_mode", "user")
    if mode == "group":
        gid = cfg.get("group_id")
        if gid and not gid.startswith("YOUR_"):
            return gid, "group"
        raise RuntimeError("target_mode=group 但 group_id 尚未設定")
    uid = cfg.get("user_id")
    if uid and not uid.startswith("YOUR_"):
        return uid, "user"
    raise RuntimeError("target_mode=user 但 user_id 尚未設定")

if __name__ == "__main__":
    # dry-run：上傳測試圖、列印網址，不推播
    test_img = os.path.join(BASE, "output", "goodmorning_20260824.png")
    if os.path.exists(test_img):
        url = upload_image(test_img)
        print("公開網址:", url)
        print("（dry-run：尚未推播。填入 token/group_id 後執行 run_daily.py 才會真正發送）")
    else:
        print("找不到測試圖，請先執行 gen_goodmorning.py")
