from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from computeforge._version import __version__
from computeforge.api.routes_actions import router as actions_router
from computeforge.api.routes_replay import router as replay_router
from computeforge.api.routes_sessions import router as sessions_router
from computeforge.api.routes_websocket import router as ws_router
from computeforge.models.config import EngineConfig
from computeforge.observability.storage import StorageBackend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.config = EngineConfig()
    app.state.storage = StorageBackend()
    await app.state.storage.connect()
    yield
    await app.state.storage.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ComputeForge API",
        description="Open-source, extensible Computer-Use Agent Platform — REST + WebSocket API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "ComputeForge Contributors",
            "email": "team@computeforge.ai",
            "url": "https://computeforge.ai",
        },
        license_info={
            "name": "Apache 2.0",
            "identifier": "Apache-2.0",
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sessions_router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(actions_router, prefix="/api/v1/actions", tags=["actions"])
    app.include_router(replay_router, prefix="/api/v1/replay", tags=["replay"])
    app.include_router(ws_router, prefix="/api/v1/ws", tags=["websocket"])

    @app.get("/api/v1/health")
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "python": __import__("sys").version,
        }

    @app.get("/api/v1/info")
    async def info():
        return {
            "name": "ComputeForge",
            "version": __version__,
            "description": "Open-source, extensible Computer-Use Agent Platform",
            "endpoints": {
                "health": "/api/v1/health",
                "sessions": "/api/v1/sessions",
                "actions": "/api/v1/actions",
                "replay": "/api/v1/replay",
                "websocket": "/api/v1/ws/sessions/{session_id}",
                "docs": "/docs",
            },
        }

    @app.get("/", response_class=HTMLResponse)
    async def root():
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head><title>ComputeForge API</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
            h1 {{ color: #2563eb; }}
            .endpoints {{ background: #f8fafc; padding: 20px; border-radius: 8px; }}
            code {{ background: #e2e8f0; padding: 2px 6px; border-radius: 4px; }}
        </style>
        </head>
        <body>
        <h1>🔧 ComputeForge API v{__version__}</h1>
        <p>Open-source Computer-Use Agent Platform</p>
        <div class="endpoints">
            <h3>Available Endpoints</h3>
            <ul>
                <li><a href="/docs"><code>/docs</code></a> — Interactive API documentation</li>
                <li><a href="/api/v1/health"><code>/api/v1/health</code></a> — Health check</li>
                <li><a href="/api/v1/info"><code>/api/v1/info</code></a> — API information</li>
                <li><code>/api/v1/sessions</code> — Session management</li>
                <li><code>/api/v1/actions</code> — Action execution</li>
                <li><code>/api/v1/replay</code> — Session replay</li>
                <li><code>/api/v1/ws/sessions/&#123;id&#125;</code> — WebSocket real-time stream</li>
            </ul>
        </div>
        <p><a href="https://computeforge.ai">computeforge.ai</a></p>
        </body>
        </html>
        """)

    return app


app = create_app()
