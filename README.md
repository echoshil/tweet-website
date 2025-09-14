# tweet-website

# 🐦 Twitter Auto Comment Bot + Dashboard

Dashboard web untuk mengelola **bot komentar otomatis Twitter/X** menggunakan **FastAPI + Tweepy + WebSocket**.  
Bisa start/pause/resume bot, mengatur interval per akun, mengupload/generate komentar, dan memonitor log secara real-time.  

---

## 🚀 Fitur
- Web dashboard dengan **FastAPI + Jinja2 Templates**
- Kontrol bot: **Start / Pause / Resume / Stop**
- Manajemen akun (interval & max komentar per akun)
- Upload file komentar (`.txt`) atau generate otomatis
- Token management langsung dari UI (update/reset `.env`)
- Progress bar jumlah komentar
- Activity log real-time via WebSocket
- **Dark/Light mode** support  

---

## 📂 Struktur Project
   .
├── bot.py
├── controller.py
├── state.py
├── account_settings.json
├── requirements.txt
├── Procfile
├── templates/
│   └── index.html
├── static/
│   └── style.css
└── .gitignore

---

## 🔧 Instalasi Lokal
1. Clone repo:
   ```bash
   git clone https://github.com/echoshil/tweet-website.git
   cd tweet-website
2. Buat virtual env & install dependencies:
   ```bash
    python -m venv venv
    source venv/bin/activate   # Linux/Mac
    venv\Scripts\activate      # Windows
    pip install -r requirements.txt

3. Buat file .env dan isi dengan token Twitter API kamu:
   ```bash
    NUM_ACCOUNTS=6
    REPLY_INTERVAL=10
    MAX_COMMENTS=20
    
    CONSUMER_KEY_1=xxxx
    CONSUMER_SECRET_1=xxxx
    ACCESS_TOKEN_1=xxxx
    ACCESS_TOKEN_SECRET_1=xxxx

4. Jalankan server:
   ```bash
    uvicorn controller:app --reload

6. Buka di browser:
   ```bash
   http://127.0.0.1:8000

🌐 Deploy ke Railway

Push project ke GitHub (pastikan .env tidak di-commit).

1. Tambahkan file Procfile dengan isi:
   ```bash
   web: uvicorn controller:app --host 0.0.0.0 --port $PORT

2. Deploy ke Railway:
- Login ke railway.app → New Project → Deploy from GitHub Repo.
- Tambahkan environment variables (isi dari .env) di Railway dashboard → Variables.

3. Railway akan memberi URL publik, misal:
   ```bash
   https://mybot.up.railway.app

