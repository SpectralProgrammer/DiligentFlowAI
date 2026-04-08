# DiligentFlowAI

📌 [Original Repository](https://github.com/heyamktr/DiligentFlowAI)

👨‍💻 Authors: 
[Shravan Devraj](https://github.com/SpectralProgrammer) and 
[Khanh Truong](https://github.com/heyamktr)

🏆 Hackathon: 
Built for Authorized to Act: Auth0 for AI Agents (Devpost)

🎥 Video Demo: https://www.youtube.com/watch?v=Qyi8kmUTg0k 

---

<div align="center">
  <img width="500" alt="image" src="https://github.com/user-attachments/assets/3b15e597-00c2-4db3-ae74-640084abe77f" />
</div>

---

DiligentFlowAI is a secure multi-agent AI system that connects to user applications and automates everyday workflows such as email management, scheduling, and task organization. Using Auth0 for AI Agents and Token Vault, it safely authenticates and authorizes access to services like email and calendar, allowing AI agents to act on the user’s behalf while maintaining full user control and consent.

The system is powered by a modular agent architecture, where specialized agents handle specific tasks such as email prioritization, summarization, and calendar planning. A central orchestration layer coordinates these agents and communicates with external APIs through secure delegated access.

DiligentFlowAI uses hosted AI models to analyze user data, generate insights, and recommend actions in real time. The result is a privacy-conscious, automated assistant that helps users stay organized and productive without manually managing their digital workflows.

---
DiligentFlowAI is a split `Next.js` + `FastAPI` application that demonstrates a simple but opinionated pattern for protected AI workflows:

- the user signs in with `Auth0`
- the frontend requests an Auth0 access token for a backend API audience
- the backend validates that token
- the backend parses the user request into an agent/action/resource tuple
- the backend checks a policy matrix
- if allowed, the backend issues a short-lived internal scoped token and runs the selected agent

The current UX is a single chat-style workspace with two modes:

- conversational AI through `/chat`
- protected action execution through `/tasks`

Optional Google OAuth support lets a signed-in user connect Gmail and Google Calendar for summaries inside the same UI.

## What This Repo Contains

```text
frontend/   Next.js 16 app, Auth0 login, backend proxy route, dashboard UI
backend/    FastAPI app, Auth0 token validation, task orchestration, Gemini integration
infra/      Placeholder infra directories from earlier work
scripts/    Misc project scripts
```

The important runtime entrypoints are:

- `frontend/app/page.tsx`: signed-out landing page and signed-in dashboard shell
- `frontend/app/api/backend/[...path]/route.ts`: authenticated proxy from Next.js to FastAPI
- `backend/app/main.py`: FastAPI app factory and route registration
- `backend/app/orchestrator/orchestrator.py`: agent selection, permission checks, token minting, task history

## Architecture

### Request Flow

1. A user opens the Next.js app.
2. Auth0 handles login through the Next.js SDK.
3. For protected API calls, the frontend gets an Auth0 access token with `AUTH0_AUDIENCE`.
4. The frontend forwards the request to FastAPI with that bearer token.
5. FastAPI validates the token against your Auth0 tenant JWKS.
6. The orchestrator parses the request into an agent/action/resource.
7. The permission layer checks whether that scope is allowed.
8. If allowed, the backend mints a 30-minute internal scoped token and runs the agent handler.
9. The frontend renders the result, audit trail, visible scopes, and recent history.

### Built-In Agents

- `email-agent`
  Sends or drafts Gmail messages.
- `calendar-agent`
  Reads or schedules Google Calendar events.
- `finance-agent`
  Handles finance and market-data prompts.

### Permission Model

The current permission layer is intentionally simple and local:

- `email-agent` -> `send:gmail-api`, `draft:gmail-api`
- `calendar-agent` -> `schedule:google-calendar`, `read:google-calendar`
- `finance-agent` -> `analyze:market-data`, `summarize:market-data`

This project calls that layer `openfga_client`, but today it is an in-memory policy matrix rather than a live OpenFGA integration.

### State And Persistence

Not all state is durable yet:

- task history is stored in memory and resets on backend restart
- Google OAuth connections are stored in SQLite
- Google access and refresh tokens are encrypted with `TOKEN_ENCRYPTION_KEY`

Because Google connections are stored in SQLite, the backend currently requires a persistent writable disk.

## Features

- Auth0-protected operator sessions
- Auth0-protected FastAPI routes
- conversational AI via Gemini
- agent-style task parsing for email, calendar, and finance prompts
- internal short-lived scoped tokens for task execution
- Google Gmail and Calendar summaries
- Dockerized frontend and backend
- single-host Docker Compose deployment path

## Example Prompts

These are the kinds of inputs the current parser and UI are built around:

- `Explain how this project uses Auth0, permissions, and short-lived tokens.`
  Goes through the conversational `/chat` flow.
- `Flag my urgent emails and draft a reply to my boss about tomorrow's review.`
  Usually maps to `email-agent`.
- `Plan my calendar around two deep work blocks tomorrow afternoon.`
  Usually maps to `calendar-agent`.
- `Analyze Nvidia and summarize the biggest market signals before lunch.`
  Usually maps to `finance-agent`.
- `Summarize my unread emails and today's calendar.`
  Uses the Google summary flow if Google is connected.

## Prerequisites

For local development:

- Node.js
- npm
- Python

For the included container deployment:

- Docker
- Docker Compose

External accounts and credentials:

- Auth0 tenant
- Auth0 `Regular Web Application`
- Auth0 API with an identifier that matches `AUTH0_AUDIENCE`
- Gemini API key
- optional Google OAuth app for Gmail and Calendar features

## Quick Start

### 1. Clone And Install

```powershell
git clone <your-repo-url>
cd Authorized-to-Act-Auth0-for-AI-Agents
Copy-Item .env.example .env
```

Install backend dependencies:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

Install frontend dependencies:

```powershell
cd frontend
npm install
cd ..
```

### 2. Fill In Environment Variables

You have two common local-dev patterns:

- keep most values in root `.env`
- keep frontend-only values in `frontend/.env.local`

The backend loads all of these during development:

- repo root `.env`
- `backend/.env`
- `frontend/.env.local`

The frontend reads its environment normally through Next.js.

### 3. Start The Backend

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Expected local URLs:

- backend root: `http://127.0.0.1:8000`
- backend docs: `http://127.0.0.1:8000/docs`
- backend health: `http://127.0.0.1:8000/healthz`

### 4. Start The Frontend

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open:

- `http://localhost:3000`

Use `localhost` consistently for the frontend during Auth0 local testing. Do not switch back and forth between `localhost:3000` and `127.0.0.1:3000`, because Auth0 transaction cookies are host-specific and that can cause `The state parameter is invalid`.

## Environment Variables

This repo uses a mix of shared, frontend-only, and backend-only values.

| Variable | Used By | Required | Purpose |
| --- | --- | --- | --- |
| `APP_BASE_URL` | frontend + backend | Yes | Public base URL of the frontend app. Also used by backend Google callback redirects. |
| `AUTH0_DOMAIN` | frontend + backend | Yes | Auth0 tenant domain, for example `example.us.auth0.com`. |
| `AUTH0_CLIENT_ID` | frontend | Yes | Auth0 application client ID. |
| `AUTH0_CLIENT_SECRET` | frontend | Yes | Auth0 application client secret. |
| `AUTH0_SECRET` | frontend | Yes | Cookie/session encryption secret for `@auth0/nextjs-auth0`. |
| `AUTH0_AUDIENCE` | frontend + backend | Yes | Auth0 API identifier requested by the frontend and verified by the backend. |
| `AUTH0_SCOPE` | frontend | Recommended | Defaults to `openid profile email`. |
| `API_BASE_URL` | frontend | Yes in production | Public backend base URL for the Next.js proxy. For Docker Compose, use `http://backend:8000`. |
| `NEXT_PUBLIC_API_BASE_URL` | frontend | Optional | Fallback client-visible API base URL. Mostly useful in local development. |
| `CORS_ORIGINS` | backend | Yes | Comma-separated allowed origins for FastAPI CORS. |
| `DATABASE_URL` | backend | Yes | Must be `sqlite:///...` with the current built-in Google token store. |
| `GEMINI_API_KEY` | backend | Yes for AI responses | Gemini API key used by the backend model layer. |
| `GEMINI_MODEL` | backend | Optional | Defaults to `gemini-2.5-flash`. |
| `GOOGLE_CLIENT_ID` | backend | Optional | Required only for Gmail and Calendar connection flows. |
| `GOOGLE_CLIENT_SECRET` | backend | Optional | Required only for Gmail and Calendar connection flows. |
| `GOOGLE_REDIRECT_URI` | backend | Optional | Exact Google OAuth callback URL. |
| `TOKEN_ENCRYPTION_KEY` | backend | Optional for pure chat, required for Google | Fernet key used to encrypt stored Google tokens and sign Google OAuth state. |

### Local Example

This is a representative local setup:

```env
APP_BASE_URL=http://localhost:3000
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_SECRET=your-auth0-cookie-secret
AUTH0_AUDIENCE=https://authorized-to-act-api
AUTH0_SCOPE=openid profile email

API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000

CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DATABASE_URL=sqlite:///backend/data/authorized_to_act.db
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.5-flash

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/backend/google/callback
TOKEN_ENCRYPTION_KEY=your-generated-fernet-key
```

### Secret Generation

Generate `AUTH0_SECRET`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate `TOKEN_ENCRYPTION_KEY`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Auth0 Setup

Create:

- an Auth0 `Regular Web Application` for the Next.js frontend
- an Auth0 API for the FastAPI backend

The API identifier must exactly match `AUTH0_AUDIENCE`.

### Local Auth0 Settings

For local development, set these in your Auth0 application:

- Allowed Callback URLs: `http://localhost:3000/auth/callback`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

### Production Auth0 Settings

For a production domain like `https://assistant.example.com`, set:

- Allowed Callback URLs: `https://assistant.example.com/auth/callback`
- Allowed Logout URLs: `https://assistant.example.com`
- Allowed Web Origins: `https://assistant.example.com`

The backend expects:

- the same Auth0 tenant as the frontend
- the same `AUTH0_AUDIENCE` as the frontend
- `RS256` signing on the Auth0 API

## Google OAuth Setup

Google support is optional. Without it, normal Auth0 login and non-Google flows still work.

If you want Gmail and Calendar summaries:

1. Create a Google OAuth client.
2. Add the exact redirect URI used by this app.
3. Provide `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, and `TOKEN_ENCRYPTION_KEY`.

Common callback values:

- local: `http://localhost:3000/api/backend/google/callback`
- production single-domain deploy: `https://assistant.example.com/api/backend/google/callback`

## API Surface

The backend exposes these main routes:

- `GET /`
  Basic app metadata and route hints.
- `GET /healthz`
  Health check plus whether Auth0 and Google config look complete.
- `POST /chat`
  Conversational AI endpoint.
- `GET /dashboard/bootstrap`
  Dashboard metadata, current agents, permissions, and recent task history.
- `POST /tasks/preview`
  Parse a free-text request into an agent/action/resource prediction.
- `POST /tasks`
  Execute a protected task through the orchestrator.
- `GET /history`
  Recent task history.
- `GET /agents`
  Registered agent definitions.
- `GET /permissions`
  Current permission matrix.
- `GET /tokens/about`
  Token model explanation.
- `GET /google/status`
  Check whether the current user has connected Google.
- `POST /google/connect`
  Start Google OAuth.
- `GET /google/callback`
  Complete Google OAuth.
- `DELETE /google/connection`
  Disconnect Google.
- `POST /google/summary`
  Build a Gmail + Calendar summary for the signed-in user.

## Local Development Workflow

### Recommended Order

1. Start the backend.
2. Start the frontend.
3. Confirm `http://localhost:3000` loads.
4. Sign in with Auth0.
5. Confirm the dashboard loads without backend errors.
6. Test `/chat`.
7. Test a protected task.
8. Test Google connection only after the first two flows work.

### Helpful Smoke Tests

Backend health:

```powershell
curl.exe http://127.0.0.1:8000/healthz
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

Frontend build:

```powershell
cd frontend
npm run build
```

Frontend lint:

```powershell
cd frontend
npm run lint
```

## Deployment

### Recommended Deployment

The most reliable deployment for this repo today is a single-host Docker Compose deployment.

Why this is the safest path:

- the frontend is a standard Next.js app
- the backend is a standard FastAPI app
- Google OAuth connections are stored in SQLite
- SQLite needs persistent disk
- the current task history is in memory, so a single backend instance keeps behavior easy to reason about

### Docker Compose

Copy your env file and start the stack:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Included services:

- `frontend`
- `backend`
- `backend-data` Docker volume for SQLite persistence

Useful commands:

```powershell
docker compose ps
docker compose logs -f frontend
docker compose logs -f backend
docker compose down
```

### Public Production Setup

For a public deployment:

1. provision a server
2. point a domain at it
3. run Docker Compose
4. put HTTPS in front of the frontend with a reverse proxy like Caddy or Nginx
5. set Auth0 and Google callback URLs to the public domain

### Vercel Status

The frontend can deploy to Vercel, but the full stack is not a clean Vercel-only fit yet.

Why:

- the frontend works well on Vercel
- the backend still needs persistent writable storage for SQLite
- `API_BASE_URL` cannot point to `127.0.0.1` on Vercel

If you deploy the frontend to Vercel before the backend is public:

- Auth0 login can work
- signed-in dashboard requests will fail
- chat and task execution will fail

For a Vercel frontend, use:

- `APP_BASE_URL=https://your-project.vercel.app`
- `API_BASE_URL=https://your-public-backend-url`

Do not use:

- `APP_BASE_URL=http://localhost:3000`
- `API_BASE_URL=http://127.0.0.1:8000`

### Vercel Frontend Checklist

If you still want to deploy the frontend to Vercel first:

1. Set the Vercel root directory to `frontend`.
2. Let Vercel detect the project as `Next.js`.
3. Set:
   - `APP_BASE_URL=https://your-project.vercel.app`
   - `AUTH0_DOMAIN=...`
   - `AUTH0_CLIENT_ID=...`
   - `AUTH0_CLIENT_SECRET=...`
   - `AUTH0_SECRET=...`
   - `AUTH0_AUDIENCE=...`
   - `AUTH0_SCOPE=openid profile email`
4. Only set `API_BASE_URL` after you have a public backend URL.
5. In Auth0, add the exact Vercel callback/logout/web-origin URLs.

Expected behavior with no public backend yet:

- the marketing/login shell can work
- Auth0 login can work
- the signed-in dashboard will fail when it tries to reach the backend
- task execution and Google features will not work

## Troubleshooting

### `The state parameter is invalid`

Most likely causes:

- `APP_BASE_URL` does not match the host you are using
- the Auth0 callback URL is not registered exactly
- you started login on `localhost` and returned to `127.0.0.1`, or the reverse

Fix:

- use `http://localhost:3000` consistently for local frontend auth
- set Auth0 callback/logout/web origin values to `localhost`
- clear cookies and try again

### `Auth0 did not return an access token`

Most likely cause:

- `AUTH0_AUDIENCE` does not exactly match the Auth0 API identifier

Fix:

- verify the Auth0 API exists
- verify the API identifier exactly matches `AUTH0_AUDIENCE`
- verify the frontend and backend use the same `AUTH0_AUDIENCE`

### `The Next.js proxy could not reach the FastAPI backend`

Most likely causes:

- backend is not running locally
- `API_BASE_URL` is wrong
- on Vercel, `API_BASE_URL` still points to localhost

Fix:

- start the backend
- check the backend health route
- update `API_BASE_URL` to a reachable backend URL

### `AUTH0_DOMAIN and AUTH0_AUDIENCE must be configured`

Most likely cause:

- the backend env file is incomplete

Fix:

- verify backend environment variables are loaded where FastAPI runs

### Google connect flow fails

Most likely causes:

- `GOOGLE_REDIRECT_URI` mismatch
- missing `TOKEN_ENCRYPTION_KEY`
- Google OAuth app not configured for the current domain

Fix:

- make the callback URL exact
- ensure `TOKEN_ENCRYPTION_KEY` is set and valid
- verify the backend can persist SQLite data

## Known Limitations

- Task history is in-memory and resets on backend restart.
- The permission layer is local and static, not yet backed by a real policy engine.
- The project name references OpenFGA/Auth0 concepts, but only Auth0 is truly externalized today.
- Vercel is suitable for the frontend, but not ideal for the backend in the current storage model.

## Suggested Next Improvements

- connect more google services to diversify project capabilities 
- replace in-memory task history with persistent storage
- move Google token storage from SQLite to a managed database
- wire the permission layer to a real policy backend
- add tests for the proxy route and Auth0 configuration edge cases
- split frontend and backend deployment instructions into dedicated docs if the project grows
