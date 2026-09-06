# Uncle's Wellness

Beauty & wellness storefront built with **FastAPI** (server-rendered pages + JSON API) on a **Firebase Firestore** database, with a SQLite fallback for local demo mode.

## Architecture

```
Browser
   │
   ▼
https://uncles-wellness.vercel.app        ← Vercel front door (reverse proxy)
   │  vercel.json rewrites "/:path*"
   ▼
https://uncles-wellness.onrender.com      ← Render backend (FastAPI + Firestore)
```

- The whole application (HTML pages, static assets, and API) is served by FastAPI on **Render**.
- **Vercel** sits in front as a CDN/reverse proxy, so the site is reachable at your `.vercel.app` domain while the backend runs on Render.

## Local development

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 3000
```

Open http://localhost:3000. Without Firebase credentials the app falls back to the local SQLite file.

## Deploying

### 1. Render (backend)

The repository includes a `render.yaml` [Blueprint](https://render.com/docs/infrastructure-as-code) for a Python web service.

Option A — Blueprint (recommended):
1. Push this repo to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com): **New → Blueprint**.
3. Connect the GitHub repo and click **Apply**. Render creates the `uncles-wellness` web service.

Option B — Manual web service:
1. **New → Web Service** → connect the GitHub repo.
2. Set:
   - Language: **Python**
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*`

After creating the service, set these environment variables (Dashboard → Environment):

| Variable | Description |
| --- | --- |
| `SESSION_SECRET_KEY` | Random secret (Blueprint generates one automatically). |
| `ALLOWED_ORIGINS` | Comma-separated allowed origins, e.g. `https://uncles-wellness.vercel.app,http://localhost:3000`. |
| `FIREBASE_PROJECT_ID` | Firebase project id. |
| `FIREBASE_PRIVATE_KEY_ID` | Service-account private key id. |
| `FIREBASE_PRIVATE_KEY` | Service-account private key (with literal `\n` line breaks). |
| `FIREBASE_CLIENT_EMAIL` | Service-account client email. |
| `FIREBASE_CLIENT_ID` | Service-account client id. |

> These are the same Firestore credential variables already supported by `firebase_db.py` (which reads them when no `GOOGLE_APPLICATION_CREDENTIALS` path or local `firebase-credentials.json` file is present). Only the `FIREBASE_*` set is needed on Render.

The app seeds Firestore with sample products on first boot when the `products` collection is empty. Seed admin login: `admin@uncleswellness.com` / `admin123` (change in production).

### 2. Vercel (front door / proxy)

The repository includes a `vercel.json` that rewrites every request to the Render backend:

```json
{
  "rewrites": [
    { "source": "/:path*", "destination": "https://uncles-wellness.onrender.com/:path*" }
  ]
}
```

1. Import this GitHub repo into Vercel (or run `vercel` CLI from the repo root). No build step is needed.
2. If your Render URL differs, update the `destination` in `vercel.json` (e.g. use `$1` capture in a `/:path*` source vs the `:path*` token) and redeploy.

The site will be live at `https://<project>.vercel.app` and proxied to Render; update `ALLOWED_ORIGINS` on Render to match your final Vercel domain.