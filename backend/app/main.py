from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.agents import router as agents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.history import router as history_router
from app.api.routes.permissions import router as permissions_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.tokens import router as tokens_router

def create_app() -> FastAPI:
    app = FastAPI(title="Authorized-to-Act Backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router)
    app.include_router(tasks_router)
    app.include_router(history_router)
    app.include_router(agents_router)
    app.include_router(permissions_router)
    app.include_router(tokens_router)

    @app.get("/")
    def root():
        return {
            "message": "Authorized-to-Act backend is running",
            "frontend_hint": "Open the Next.js app to preview routes, submit tasks, and inspect decisions.",
            "available_routes": [
                "/chat",
                "/tasks",
                "/tasks/preview",
                "/history",
                "/agents",
                "/permissions",
                "/tokens/about",
            ],
        }

    return app


app = create_app()
