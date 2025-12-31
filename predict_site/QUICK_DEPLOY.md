# Quick Deployment Guide - Streamlit Cloud (FREE)

## Easiest & Cheapest Option: Streamlit Community Cloud

**Cost:** FREE (unlimited public apps)

## Steps:

### 1. Prepare Your Repository

Make sure you have:
- ✅ `requirements.txt` (already created)
- ✅ `predict_site/app.py` (your Streamlit app)
- ✅ All necessary code modules

### 2. Handle the Database

**Option A: Include in repo** (if < 100MB)
```bash
# Remove from .gitignore temporarily
git add data/ufc_database.db
git commit -m "Add database for deployment"
```

**Option B: Use cloud storage** (recommended for large DB)
- Upload `data/ufc_database.db` to:
  - Google Drive (public link)
  - Dropbox (public link)
  - AWS S3 / Cloudflare R2
  - GitHub Releases (if < 100MB)

Then modify `predict_site/app.py` to download on first run:
```python
import urllib.request
import os

DB_URL = os.getenv("DB_URL", "https://your-link.com/ufc_database.db")
DB_PATH = "data/ufc_database.db"

if not os.path.exists(DB_PATH):
    os.makedirs("data", exist_ok=True)
    urllib.request.urlretrieve(DB_URL, DB_PATH)
```

### 3. Push to GitHub

```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### 4. Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `ufc-analysis-v2`
5. Main file path: `predict_site/app.py`
6. Python version: `3.12`
7. Click "Deploy"

### 5. Configure Secrets (if using cloud DB)

If using Option B for database:
- Go to app settings
- Add secret: `DB_URL` = your database URL

## That's it! Your app will be live at:
`https://your-app-name.streamlit.app`

## Alternative: Render (also FREE)

If Streamlit Cloud doesn't work:

1. Go to https://render.com
2. New → Web Service
3. Connect GitHub repo
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `streamlit run predict_site/app.py --server.port $PORT --server.address 0.0.0.0`
5. Deploy

## Cost Comparison

| Platform | Cost | Setup Time | Best For |
|----------|------|------------|----------|
| **Streamlit Cloud** | FREE | 5 min | Easiest |
| **Render** | FREE | 10 min | More control |
| **Railway** | FREE ($5 credit) | 10 min | Flexible |
| **Fly.io** | FREE (3 VMs) | 15 min | Global |

**Recommendation:** Start with **Streamlit Cloud** - it's literally the easiest!

