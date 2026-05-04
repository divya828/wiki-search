# Wiki Search

Wikipedia search & Q&A tool. Scrapes on demand, embeds locally, retrieves with hybrid pgvector + tsvector, answers with Claude.

## Local development

1. `python3 -m venv .venv && source .venv/bin/activate` (Python 3.11+)
2. `pip install -r backend/requirements.txt`
3. `cp .env.example .env` and fill in values
4. `cd backend && uvicorn app.main:app --reload`
5. (Frontend) `cd web && npm install && npm run dev`

## Deploy

See Dockerfile and `docs/deploy.md` (TODO post-launch).
