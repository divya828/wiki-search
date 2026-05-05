# Deploy to Railway

1. Push the repo to GitHub (already done).
2. Go to https://railway.app, sign in with GitHub.
3. New Project → Deploy from GitHub → pick `divya828/wiki-search`.
4. Railway auto-detects the Dockerfile.
5. Add environment variables in the Railway service settings:
   - `ANTHROPIC_API_KEY` — from https://console.anthropic.com/settings/keys
   - `DATABASE_URL` — Supabase Session pooler connection string (URL-encode special chars in password)
6. Railway exposes a `*.up.railway.app` URL once the build finishes (~5-10 minutes for first build because of torch + embedding model download).
7. Open the URL and test the same Marie Curie / Roman Empire / ancient civilizations flows used in local dev.

## Local Docker test

```bash
docker build -t wiki-search .
docker run --rm -p 8000:8000 --env-file .env wiki-search
```

Open http://localhost:8000 in a browser.
