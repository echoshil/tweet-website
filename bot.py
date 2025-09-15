import os
import time
from typing import Dict, Tuple, List
import tweepy
from dotenv import load_dotenv
import state
import json
import requests

# -------------------------------------------------------------------
# ⚠️ WARNING: Auto comment bisa dianggap spam oleh Twitter/X.
# Gunakan dengan hati-hati, patuhi Terms of Service & rate limit.
# -------------------------------------------------------------------

load_dotenv()

# ====== Inisialisasi Akun ======
accounts: List[Tuple[int, tweepy.Client]] = []
for i in range(1, 7):
    ck = os.getenv(f"CONSUMER_KEY_{i}")
    cs = os.getenv(f"CONSUMER_SECRET_{i}")
    at = os.getenv(f"ACCESS_TOKEN_{i}")
    ats = os.getenv(f"ACCESS_TOKEN_SECRET_{i}")
    if ck and cs and at and ats:
        try:
            client = tweepy.Client(
                consumer_key=ck,
                consumer_secret=cs,
                access_token=at,
                access_token_secret=ats,
                wait_on_rate_limit=True
            )
            accounts.append((i, client))
            print(f"✅ Akun {i} siap dipakai")
        except Exception as e:
            print(f"❌ Gagal inisialisasi akun {i}: {e}")

# ====== Logging ======
def log_message(msg: str):
    print(msg, flush=True)
    try:
        with open("logs.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ====== Helpers ======
def load_comments(account_id: int):
    try:
        with open(f"comments_{account_id}.txt", "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def save_comments(account_id: int, comments: List[str]):
    with open(f"comments_{account_id}.txt", "w", encoding="utf-8") as f:
        for c in comments:
            f.write(c + "\n")

def load_tweet_id(account_id: int):
    try:
        with open(f"tweets_{account_id}.txt", "r", encoding="utf-8") as f:
            v = f.read().strip()
            return v if v else None
    except FileNotFoundError:
        return None

def load_account_settings() -> Dict[str, Dict]:
    try:
        with open("account_settings.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ====== Main Bot ======
async def main():
    state.bot_running = True
    log_message("🚀 Bot started")

    processed_counts: Dict[int, int] = {}

    while state.bot_running:
        if state.bot_paused:
            time.sleep(1)
            continue

        settings = load_account_settings()

        for acc_id, client in accounts:
            if not state.bot_running:
                break

            acc_settings = settings.get(str(acc_id), {})
            interval = max(60, int(acc_settings.get("interval", 60)))  # minimal 60 detik
            max_comments = int(acc_settings.get("max_comments", 20))
            processed_counts.setdefault(acc_id, 0)

            if processed_counts[acc_id] >= max_comments:
                log_message(f"⏱️ Account {acc_id}: limit {max_comments} tercapai")
                continue

            tweet_id = load_tweet_id(acc_id)
            if not tweet_id:
                log_message(f"⚠️ Account {acc_id}: Tweet ID belum di-set")
                continue

            comments = load_comments(acc_id)
            if not comments:
                log_message(f"⚠️ Account {acc_id}: Tidak ada komentar di file")
                continue

            comment = comments.pop(0)

            success = False
            for attempt in range(3):
                try:
                    client.create_tweet(text=comment, in_reply_to_tweet_id=tweet_id)
                    processed_counts[acc_id] += 1
                    log_message(
                        f"✅ Account {acc_id} commented ({processed_counts[acc_id]}/{max_comments}): {comment}"
                    )
                    success = True
                    break
                except tweepy.Forbidden as e:
                    log_message(f"🛑 Account {acc_id} Forbidden: {e}")
                    break
                except tweepy.TooManyRequests as e:
                    # Rate limit → tunggu 15 menit penuh
                    log_message(f"⏳ Account {acc_id} rate-limited: tidur 15 menit ({e})")
                    time.sleep(15 * 60)
                except tweepy.Unauthorized as e:
                    log_message(f"🔑 Account {acc_id} unauthorized: {e}")
                    break
                except requests.exceptions.RequestException as e:
                    log_message(f"⚠️ Account {acc_id} network error: {e} (retry {attempt+1}/3)")
                    time.sleep(10)
                except Exception as e:
                    err = str(e).lower()
                    if "suspend" in err:
                        log_message(f"🚫 Account {acc_id} kemungkinan suspended: {e}")
                    else:
                        log_message(f"❌ Account {acc_id} error: {e}")
                    break

            save_comments(acc_id, comments)

            # Delay antar akun
            time.sleep(5)

            # Tunggu sesuai interval sebelum akun ini komentar lagi
            waited = 0
            while waited < interval:
                if not state.bot_running:
                    break
                while state.bot_paused and state.bot_running:
                    time.sleep(1)
                time.sleep(1)
                waited += 1

    log_message("⛔ Bot stopped")
