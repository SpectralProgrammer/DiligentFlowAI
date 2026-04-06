# Authorized to Act

Authorized to Act is a split Next.js and FastAPI application that uses Auth0 for user sessions, proxies protected API calls through the frontend, and can optionally connect Gmail and Google Calendar for summaries.

## Deployment Path

The safest deployment for this repo today is a single-host Docker Compose deployment with:

- `frontend`: Next.js 16 + Auth0
- `backend`: FastAPI + Gemini + Google OAuth token storage
- `backend-data`: a persistent Docker volume for the SQLite database used by Google connections

This works well on a VPS, a small cloud VM, or any platform that can run Docker Compose.

## Before You Deploy

You need:

- Docker and Docker Compose
- An Auth0 `Regular Web Application`
- An Auth0 API configured with an identifier that matches `AUTH0_AUDIENCE`
- A Gemini API key
- Optional: a Google OAuth client if you want Gmail and Calendar summaries

## Environment Setup

1. Copy the template:

```powershell
Copy-Item .env.example .env
```

2. Fill in `.env`.

Important values:

- `APP_BASE_URL`: the public HTTPS URL for the frontend, for example `https://assistant.example.com`
- `API_BASE_URL`: for Docker Compose, keep this as `http://backend:8000`
- `AUTH0_SECRET`: generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `AUTH0_DOMAIN`: your Auth0 tenant domain, for example `example.us.auth0.com`
- `AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET`: from the Auth0 application
- `AUTH0_AUDIENCE`: your Auth0 API identifier
- `CORS_ORIGINS`: set this to your frontend origin, for example `https://assistant.example.com`
- `GEMINI_API_KEY`: your Gemini API key
- `TOKEN_ENCRYPTION_KEY`: generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- `GOOGLE_REDIRECT_URI`: for a single-domain deploy, set this to `https://assistant.example.com/api/backend/google/callback`

## Auth0 Configuration

Create or update your Auth0 application as a `Regular Web Application`, then set:

- Allowed Callback URLs: `https://assistant.example.com/auth/callback`
- Allowed Logout URLs: `https://assistant.example.com`
- Allowed Web Origins: `https://assistant.example.com`

Your Auth0 API should:

- Use the same identifier as `AUTH0_AUDIENCE`
- Use `RS256`

## Google OAuth Configuration

If you want Gmail and Calendar summaries, configure a Google OAuth client and add:

- Authorized redirect URI: `https://assistant.example.com/api/backend/google/callback`

If you deploy the backend on a separate public domain instead of using the frontend proxy, use the backend callback URL instead and update `GOOGLE_REDIRECT_URI` to match exactly.

## Start The Stack

```powershell
docker compose up --build -d
```

The services will be available at:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health check: `http://localhost:8000/healthz`

## Verify The Deployment

Check container status:

```powershell
docker compose ps
```

Check backend health:

```powershell
curl.exe http://localhost:8000/healthz
```

Then:

1. Open the frontend.
2. Sign in with Auth0.
3. Confirm the dashboard loads.
4. Send a chat request.
5. If Google is configured, test the connect flow.

## Notes And Constraints

- The frontend now builds in standalone mode for container deployment.
- The backend currently expects `DATABASE_URL` to use `sqlite:///...` for the built-in Google token store.
- Because of that SQLite requirement, you should keep the `backend-data` volume persistent in production.
- If you deploy frontend and backend as separate services later, keep `APP_BASE_URL`, `API_BASE_URL`, `CORS_ORIGINS`, and `GOOGLE_REDIRECT_URI` aligned with the public URLs you choose.

## Local Non-Docker Development

If you want to run the services without Docker:

- Frontend runs from `frontend`
- Backend runs from `backend`

Typical commands:

```powershell
# backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

```powershell
# frontend
cd frontend
npm install
npm run dev
```
