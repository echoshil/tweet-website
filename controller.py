import os
import asyncio
import threading
import json
from fastapi import FastAPI, Request, Form, WebSocket, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import bot
import state

app = FastAPI(title="Twitter Bot Dashboard")

# Static & Templates
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SETTINGS_FILE = "account_settings.json"
MAX_COMMENTS_FALLBACK = 20

# ---------- Helpers ----------
def run_bot():
    # Jalankan loop utama bot (async) di thread terpisah
    asyncio.run(bot.main())

def load_tweet_id(account_id: int):
    try:
        with open(f"tweets_{account_id}.txt", "r", encoding="utf-8") as f:
            return f.read().strip() or "No Tweet ID"
    except FileNotFoundError:
        return "No Tweet ID"

def load_comments_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def preview_comments(account_id: int, limit: int = 5):
    filename = f"comments_{account_id}.txt"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        if not lines:
            return []
        head = lines[:limit]
        tail = lines[-limit:] if len(lines) > limit else []
        body = ["..."] if tail and len(lines) > limit * 2 else []
        return head + body + tail
    except FileNotFoundError:
        return []

def load_logs(limit=100):
    try:
        with open("logs.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [line.rstrip("\n") for line in lines[-limit:]]
    except FileNotFoundError:
        return []

# ----- Account settings (interval & max per akun) -----
def load_account_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_account_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

# ----- .env token management -----
def mask_token(value: str):
    if not value:
        return ""
    if len(value) <= 8:
        return value
    return value[:4] + "..." + value[-4:]

def load_env_tokens(account_id: int):
    tokens = {"CONSUMER_KEY": "", "CONSUMER_SECRET": "", "ACCESS_TOKEN": "", "ACCESS_TOKEN_SECRET": ""}
    if not os.path.exists(".env"):
        return tokens
    with open(".env", "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith(f"CONSUMER_KEY_{account_id}="):
            tokens["CONSUMER_KEY"] = mask_token(line.split("=", 1)[1])
        elif line.startswith(f"CONSUMER_SECRET_{account_id}="):
            tokens["CONSUMER_SECRET"] = mask_token(line.split("=", 1)[1])
        elif line.startswith(f"ACCESS_TOKEN_{account_id}="):
            tokens["ACCESS_TOKEN"] = mask_token(line.split("=", 1)[1])
        elif line.startswith(f"ACCESS_TOKEN_SECRET_{account_id}="):
            tokens["ACCESS_TOKEN_SECRET"] = mask_token(line.split("=", 1)[1])
    return tokens

def update_env_variable(key: str, value: str):
    # Create or update key in .env
    old = []
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            old = f.readlines()
    found = False
    buf = []
    for line in old:
        if line.startswith(f"{key}="):
            buf.append(f"{key}={value}\n")
            found = True
        else:
            buf.append(line)
    if not found:
        buf.append(f"{key}={value}\n")
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(buf)

# ----- Compose status for UI -----
def get_status_data():
    settings = load_account_settings()
    accounts_data = []
    # Pastikan bot.accounts sudah disiapkan pada bot import
    for acc_id, _client in bot.accounts:
        cfile = f"comments_{acc_id}.txt"
        comments = load_comments_file(cfile)
        tweet_target = load_tweet_id(acc_id)
        preview = preview_comments(acc_id)
        acc_settings = settings.get(str(acc_id), {"interval": 15, "max_comments": MAX_COMMENTS_FALLBACK})
        tokens = load_env_tokens(acc_id)
        accounts_data.append({
            "id": acc_id,
            "comments_left": len(comments),
            "tweet_id": tweet_target,
            "preview": preview,
            "interval": int(acc_settings.get("interval", 15)),
            "max_comments": int(acc_settings.get("max_comments", MAX_COMMENTS_FALLBACK)),
            "tokens": tokens
        })

    return {
        "status": "Paused" if state.bot_paused else ("Running" if state.bot_running else "Stopped"),
        "accounts": accounts_data,
        "logs": load_logs()
    }

# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, **get_status_data()})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(get_status_data())
            await asyncio.sleep(2)
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ---- Bot control ----
@app.post("/start")
async def start_bot():
    if not state.bot_running:
        state.bot_running = True
        t = threading.Thread(target=run_bot, daemon=True)
        t.start()
    return RedirectResponse("/", status_code=303)

@app.post("/stop")
async def stop_bot():
    state.bot_running = False
    return RedirectResponse("/", status_code=303)

@app.post("/pause")
async def pause_bot():
    state.bot_paused = True
    return RedirectResponse("/", status_code=303)

@app.post("/resume")
async def resume_bot():
    state.bot_paused = False
    return RedirectResponse("/", status_code=303)

# ---- Logs ----
@app.post("/clear_logs")
async def clear_logs():
    open("logs.txt", "w", encoding="utf-8").close()
    return RedirectResponse("/", status_code=303)

# ---- Account settings ----
@app.post("/update_account_settings/{account_id}")
async def update_account_settings(account_id: int, interval: int = Form(...), max_comments: int = Form(...)):
    settings = load_account_settings()
    settings[str(account_id)] = {"interval": int(interval), "max_comments": int(max_comments)}
    save_account_settings(settings)
    return RedirectResponse("/", status_code=303)

# ---- Comments management ----
@app.post("/upload_comments/{account_id}")
async def upload_comments(account_id: int, file: UploadFile = File(...)):
    contents = await file.read()
    filename = f"comments_{account_id}.txt"
    with open(filename, "a", encoding="utf-8") as f:
        text = contents.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        f.write(("\n" if os.path.exists(filename) else "") + text)
    return RedirectResponse("/", status_code=303)

@app.post("/generate_comments/{account_id}")
async def generate_comments(account_id: int, base_text: str = Form(...), total: int = Form(...), mode: str = Form("overwrite")):
    filename = f"comments_{account_id}.txt"
    file_mode = "a" if mode == "append" else "w"
    with open(filename, file_mode, encoding="utf-8") as f:
        for i in range(1, int(total) + 1):
            f.write(f"{base_text} {i}\n")
    return RedirectResponse("/", status_code=303)

# ---- Tweet ID ----
@app.post("/update_tweet/{account_id}")
async def update_tweet(account_id: int, tweet_id: str = Form(...)):
    with open(f"tweets_{account_id}.txt", "w", encoding="utf-8") as f:
        f.write(tweet_id.strip())
    return RedirectResponse("/", status_code=303)

# ---- Tokens (.env) ----
@app.post("/update_tokens/{account_id}")
async def update_tokens(
    account_id: int,
    consumer_key: str = Form(...),
    consumer_secret: str = Form(...),
    access_token: str = Form(...),
    access_token_secret: str = Form(...)
):
    update_env_variable(f"CONSUMER_KEY_{account_id}", consumer_key.strip())
    update_env_variable(f"CONSUMER_SECRET_{account_id}", consumer_secret.strip())
    update_env_variable(f"ACCESS_TOKEN_{account_id}", access_token.strip())
    update_env_variable(f"ACCESS_TOKEN_SECRET_{account_id}", access_token_secret.strip())
    return RedirectResponse("/", status_code=303)

@app.post("/reset_tokens/{account_id}")
async def reset_tokens(account_id: int):
    keys = [
        f"CONSUMER_KEY_{account_id}",
        f"CONSUMER_SECRET_{account_id}",
        f"ACCESS_TOKEN_{account_id}",
        f"ACCESS_TOKEN_SECRET_{account_id}"
    ]
    if not os.path.exists(".env"):
        return RedirectResponse("/", status_code=303)
    with open(".env", "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = [line for line in lines if not any(line.startswith(k + "=") for k in keys)]
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return RedirectResponse("/", status_code=303)
