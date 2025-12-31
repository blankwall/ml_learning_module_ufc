# Streamlit App Deployment Guide

## Option 1: Streamlit Cloud (Recommended - FREE)

**Best for:** Quick deployment, zero cost, minimal setup

### Steps:

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/ufc-analysis-v2.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io/
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Set main file path: `predict_site/app.py`
   - Click "Deploy"

3. **Configure environment**
   - Streamlit Cloud will auto-detect dependencies from `pyproject.toml`
   - You may need to add a `requirements.txt` if `pyproject.toml` isn't detected
   - For the database, you'll need to upload `data/ufc_database.db` to the repo or use a cloud database

### Limitations:
- Free tier: Public apps only
- Database file size limits (may need to use cloud database for large DB)
- 1GB RAM limit

### Cost: FREE

---

## Option 2: Render (FREE tier available)

**Best for:** More control, private apps possible

### Steps:

1. **Create `render.yaml`** in project root:
   ```yaml
   services:
     - type: web
       name: ufc-predictions
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: streamlit run predict_site/app.py --server.port $PORT --server.address 0.0.0.0
       envVars:
         - key: PYTHON_VERSION
           value: 3.12.0
   ```

2. **Create `requirements.txt`** (extract from pyproject.toml):
   ```bash
   # Generate from pyproject.toml
   pip-compile pyproject.toml -o requirements.txt
   ```

3. **Deploy on Render**
   - Connect GitHub repo
   - Render auto-detects the service
   - Deploy

### Cost: FREE (with limitations), $7/month for private apps

---

## Option 3: Railway (FREE tier available)

**Best for:** Easy deployment, good free tier

### Steps:

1. **Install Railway CLI** (optional):
   ```bash
   npm i -g @railway/cli
   railway login
   ```

2. **Deploy**:
   - Connect GitHub repo on Railway dashboard
   - Add Python service
   - Set start command: `streamlit run predict_site/app.py --server.port $PORT`
   - Deploy

### Cost: FREE ($5 credit/month), then pay-as-you-go

---

## Option 4: Fly.io (FREE tier)

**Best for:** Global deployment, good performance

### Steps:

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Create `Dockerfile`**:
   ```dockerfile
   FROM python:3.12-slim
   
   WORKDIR /app
   
   COPY pyproject.toml .
   RUN pip install --no-cache-dir -e .
   RUN pip install streamlit
   
   COPY . .
   
   EXPOSE 8080
   CMD ["streamlit", "run", "predict_site/app.py", "--server.port", "8080", "--server.address", "0.0.0.0"]
   ```

3. **Deploy**:
   ```bash
   fly launch
   fly deploy
   ```

### Cost: FREE (3 shared VMs), then pay-as-you-go

---

## Database Considerations

For all platforms, you have options:

### Option A: Include DB in repo (simplest)
- Add `data/ufc_database.db` to git (if < 100MB)
- Works for Streamlit Cloud, Render, Railway

### Option B: Use cloud database (recommended for production)
- **SQLite on S3/R2**: Upload DB to object storage, download on startup
- **PostgreSQL**: Use free tiers (Supabase, Neon, Railway)
- **SQLite Cloud**: Services like Turso

### Option C: Download DB on startup
```python
# In app.py, add at the top:
import urllib.request
import os

DB_URL = os.getenv("DB_URL", "https://your-storage.com/ufc_database.db")
DB_PATH = "data/ufc_database.db"

if not os.path.exists(DB_PATH):
    os.makedirs("data", exist_ok=True)
    urllib.request.urlretrieve(DB_URL, DB_PATH)
```

---

## Quick Start: Streamlit Cloud (Recommended)

1. **Create `requirements.txt`** (if needed):
   ```bash
   # Extract from pyproject.toml dependencies
   pip install pip-tools
   pip-compile pyproject.toml -o requirements.txt
   ```

2. **Ensure database is accessible**:
   - Option 1: Add to repo (if small enough)
   - Option 2: Use environment variable for DB URL
   - Option 3: Download on first run

3. **Push to GitHub and deploy on Streamlit Cloud**

### Minimal `requirements.txt` for Streamlit Cloud:
```
streamlit>=1.28.0
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
xgboost>=2.0.0
sqlalchemy>=2.0.0
loguru>=0.7.0
pyyaml>=6.0.0
openpyxl>=3.1.5
```

---

## Cost Comparison

| Platform | Free Tier | Paid Starting | Best For |
|----------|-----------|---------------|----------|
| **Streamlit Cloud** | ✅ Yes | N/A | Easiest, public apps |
| **Render** | ✅ Yes | $7/mo | Private apps |
| **Railway** | ✅ $5 credit | Pay-as-you-go | Flexible |
| **Fly.io** | ✅ 3 VMs | Pay-as-you-go | Global performance |
| **Heroku** | ❌ No | $5/mo | Legacy option |

**Recommendation:** Start with **Streamlit Cloud** - it's free, easy, and perfect for showcasing/testing.

