#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
每日定時執行：生成當天早安圖 -> 上傳圖床 -> 推播到 LINE 群組。
排程（工作排程器）會呼叫 run_daily.bat，bat 再呼叫本檔。
失敗會寫日誌，不會靜默失敗。
"""
import os, sys, json, traceback
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(BASE, "logs")
os.makedirs(LOGDIR, exist_ok=True)

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(os.path.join(LOGDIR, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    # 避免並發：lock file（cron 多次觸發時只讓一個跑）
    import fcntl
    lock_path = os.path.join(BASE, ".run_daily.lock")
    lock_fd = open(lock_path, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        log("=== 已有任務在執行中，本次跳過 ===")
        lock_fd.close()
        return 0
    try:
        _main()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            os.remove(lock_path)
        except OSError:
            pass
    return 0

def _main():
    # 避免繼承到 venv 的舊 requests（參考 memory 記載的坑）
    os.environ.pop("PYTHONPATH", None)
    sys.path.insert(0, BASE)

    from gen_goodmorning import main as gen_main
    import push_goodmorning as push

    log("=== 開始每日早安圖任務 ===")
    cfg = push.load_config()
    token = cfg.get("channel_access_token")
    if not token or token.startswith("YOUR_"):
        log("錯誤：config.json 尚未填入 channel_access_token")
        return 1

    # 確認推播對象已設定
    try:
        push.resolve_target(cfg)
    except RuntimeError as e:
        log("錯誤：" + str(e))
        return 1

    # 1) 生成圖
    img_path = gen_main()
    log(f"生成圖片: {img_path}")

    # 2) 上傳圖床
    url = push.upload_image(img_path)
    log(f"上傳網址: {url}")

    # 3) 推播
    to, mode = push.resolve_target(cfg)
    push.push_to_line(token, to, url)
    log(f"=== 推播成功 ({mode}) ===")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("任務失敗：" + str(e))
        log(traceback.format_exc())
        sys.exit(1)
