# Demand Zone Scanner — Streamlit App

## Local setup (2 minutes)

```bash
pip install -r requirements.txt
```

Add your Neon connection string to `.streamlit/secrets.toml`:
```toml
DATABASE_URL = "postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require"
```

Run:
```bash
streamlit run app.py
```

App opens at http://localhost:8501. Edit `app.py` and save — it hot-reloads instantly.

---

## Deploy to Streamlit Community Cloud (free, public URL)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io → New app → pick your repo
3. Add your secret: Settings → Secrets → paste the `DATABASE_URL` line
4. Deploy — you get a public URL like `https://yourapp.streamlit.app`

Re-deploy = just `git push`. No build step.

---

## Sidebar controls

| Control | What it does |
|---|---|
| As of date | Replay scanner at any historical date |
| Market | US / IN (NSE) / ALL |
| Zone grade | Filter A / B / C |
| Price vs zone | above_zone or inside_zone |
| Max % above zone | Hide stocks too far from zone |

## Neon connection note

The app uses `@st.cache_resource` to keep the DB connection alive across reruns.
If you get a stale connection error after a long idle period, just refresh the page
(Streamlit will recreate it automatically).
