#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日 08:00 摘要：列出今日定時工作 + 今早備份/LINE 執行結果，推播到 LINE（早安小幫手）。
讀取來源：
  - /home/jack/backup_201_smb.last         （每次執行會清空重寫，故內容=最新一場）
  - /home/work/backup_206.log         （同上）
  - <本目錄>/logs/run.log             （LINE 早安圖，append 模式，取最後 60 行判斷）
token/user_id 取自同目錄 config.json（與 run_daily.py 共用）。
"""
import os, json, datetime, subprocess, requests

BASE = os.path.dirname(os.path.abspath(__file__))

def load_config():
    with open(os.path.join(BASE, "config.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def read_log(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""

def tail(path, n=60):
    try:
        out = subprocess.check_output(["tail", "-n", str(n), path],
                                      stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        return out
    except Exception:
        return ""

def backup_status(logtext, name):
    if not logtext.strip():
        return f"⚠️ {name}：無日誌（可能未執行）"
    # 來源離線/未開機 → 跳過（不算失敗）
    if "SKIPPED" in logtext or "離線" in logtext:
        return f"⏭️ {name}：201 離線/未開機，跳過（無資料遺失，開機後下次備）"
    rcs = []
    for line in logtext.splitlines():
        if "rc=" in line:
            try:
                rc = int(line.split("rc=")[1].strip())
                rcs.append(rc)
            except Exception:
                pass
    if not rcs:
        return f"❓ {name}：日誌存在但無 rc 記錄"
    # robocopy 退出碼語義: 0=無異動 1=複製 2=額外(鏡像清) 3=1+2 均成功; 8+=有失敗
    # 只有 rc>=8 (bit3 失敗位元) 才算失敗
    bad = [r for r in rcs if r >= 8]
    if bad:
        return f"❌ {name}：失敗（rc={bad}）"
    succ = len(rcs)
    return f"✅ {name}：成功（{succ} 項, rc={rcs}）"

def line_status(logtext):
    if not logtext.strip():
        return "⚠️ LINE：無日誌"
    # 多 instance 並發時，只要任一次推播成功即算成功
    if "=== 推播成功 (user) ===" in logtext or "推播成功" in logtext:
        return "✅ LINE 早安圖：已推播"
    seg_low = logtext.lower()
    if "traceback" in seg_low or "exception" in seg_low or "syntaxerror" in seg_low or "任務失敗" in logtext:
        return "❌ LINE 早安圖：最近一次任務執行異常（見 run.log 末段）"
    if "推送" in logtext or "push" in seg_low or "成功" in logtext:
        return "✅ LINE 早安圖：已推播"
    return "✅ LINE 早安圖：日誌無明確錯誤"

def main():
    cfg = load_config()
    token = cfg.get("channel_access_token")
    uid = cfg.get("user_id")
    if not token or not uid:
        print("缺少 channel_access_token / user_id，無法推播")
        return

    today = datetime.date.today().strftime("%Y-%m-%d")
    b201 = read_log("/home/jack/backup_201_smb.last")
    b206 = read_log("/home/work/backup_206.log")
    line_log = tail(os.path.join(BASE, "logs", "run.log"), 60)

    lines = []
    lines.append(f"📋 每日摘要 {today}")
    lines.append("")
    lines.append("【今日定時工作】")
    lines.append("• 03:00 備份 201 (Jack PC) → NAS")
    lines.append("• 04:00 備份 206 (Work PC) → NAS")
    lines.append("• 07:30 LINE 早安圖推送")
    lines.append("")
    lines.append("【最新執行結果】")
    lines.append(backup_status(b201, "備份 201"))
    lines.append(backup_status(b206, "備份 206"))
    lines.append(line_status(line_log))

    text = "\n".join(lines)
    print(text)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"to": uid, "messages": [{"type": "text", "text": text}]}
    r = requests.post("https://api.line.me/v2/bot/message/push",
                      headers=headers, json=body, timeout=30)
    print(f"[push] HTTP {r.status_code} {r.text[:200]}")
    r.raise_for_status()

if __name__ == "__main__":
    main()
