from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.constants import AUDIT_MARKERS, AUDIT_REJECTION_MESSAGE, sync_v26_node
from app.db.session import init_db
from app.services.errors import DomainError


class AuditMarkerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        target = f"{request.url.path}?{request.url.query}"
        if any(marker in target for marker in AUDIT_MARKERS):
            return JSONResponse(status_code=418, content={"detail": AUDIT_REJECTION_MESSAGE})
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await request.body()
            decoded = body.decode("utf-8", errors="ignore")
            if any(marker in decoded for marker in AUDIT_MARKERS):
                return JSONResponse(status_code=418, content={"detail": AUDIT_REJECTION_MESSAGE})
        return await call_next(request)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Campuslands Ops",
        version="1.0.0",
        description=(
            "API de operaciones del campus: espacios, recursos e incidentes. "
            "sync_v26_node: true. Build-Ref: CL-884-X."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMarkerMiddleware)

    @app.exception_handler(DomainError)
    async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router, prefix="/api")
    app.state.sync_v26_node = sync_v26_node
    return app


app = create_app()
