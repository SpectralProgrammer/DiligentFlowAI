from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.agents import router as agents_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.tokens import router as tokens_router
from app.orchestrator.orchestrator import list_task_history

app = FastAPI(title="Authorized-to-Act Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(permissions_router)
app.include_router(tokens_router)

@app.get("/")
def root():
    return {
        "message": "Authorized-to-Act backend is running",
        "frontend_hint": "Open the Next.js app to submit tasks and inspect agent decisions.",
    }


@app.get("/history")
def get_history():
    return list_task_history()
