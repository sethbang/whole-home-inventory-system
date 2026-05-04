import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .jobs import get_arq_pool
from .logging_config import setup_logging
from .middleware.request_id import RequestIdMiddleware
from .rate_limit import limiter, rate_limit_exceeded_handler
from .routers import (
    analytics,
    auth,
    backups,
    ebay,
    facebook,
    images,
    items,
    jobs,
    llm_config,
    pricing,
    vision,
)
from .settings import settings
from .telemetry import setup_telemetry

# Configure structlog + stdlib logging before the rest of the app boots so
# every module's logger picks up the shared renderer on first use.
setup_logging()
logger = logging.getLogger(__name__)

UPLOAD_DIR = str(settings.upload_path)
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info("upload directory: %s", UPLOAD_DIR)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App-wide startup/shutdown hooks.

    Today this is the ARQ Redis pool. When ``settings.REDIS_URL`` is
    unset ``get_arq_pool`` returns ``None`` and every enqueuer in the
    service layer falls back to its synchronous path — so the default
    dev stack (no Redis) still works end-to-end.
    """
    app.state.arq = await get_arq_pool()
    if app.state.arq is None:
        logger.info(
            "ARQ pool not configured (REDIS_URL unset); "
            "service-layer enqueuers will run synchronously in-request"
        )
    else:
        logger.info("ARQ pool connected")
    try:
        yield
    finally:
        if app.state.arq is not None:
            await app.state.arq.close(close_connection_pool=True)
            logger.info("ARQ pool closed")


app = FastAPI(
    title="WHIS - Whole-Home Inventory System",
    description="A self-hosted platform for managing household inventories",
    version="3.1.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

# OpenTelemetry setup is a no-op unless OTEL_ENABLED=true. When enabled
# it installs a tracer provider, an OTLP gRPC exporter, and instrumentors
# for FastAPI + SQLAlchemy. Runs after FastAPI() but before routes are
# included so the instrumentation wraps everything.
setup_telemetry(app)

# Rate limiter state lives on app.state; slowapi finds it there.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(405)
async def method_not_allowed_handler(request, exc):
    return JSONResponse(
        status_code=405,
        content={"detail": "Method not allowed"},
        headers=get_cors_headers(request),
    )


CORS_ORIGINS = settings.CORS_ORIGINS
CORS_ALLOW_METHODS = settings.CORS_ALLOW_METHODS
CORS_ALLOW_HEADERS = settings.CORS_ALLOW_HEADERS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=[
        "Content-Type",
        "Content-Disposition",
        "Authorization",
        "X-Request-ID",
    ],
    max_age=3600,
)

# Install after CORS so CORS headers are set on every response (including
# the ones where request_id binding happens). Middleware is LIFO: last
# added runs first on the way in, last on the way out — so RequestId wraps
# the inner response before CORS decorates it.
app.add_middleware(RequestIdMiddleware)


@app.middleware("http")
async def add_cors_and_trailing_slash(request, call_next):
    try:
        response = await call_next(request)
        response.headers.update(get_cors_headers(request))

        # Tolerate trailing-slash mismatches between callers and routes.
        # When a router declares `POST /items/` but a client posts to
        # `/items`, Starlette responds 405 Method Not Allowed (because
        # `GET /items` exists but `POST /items` does not). Send a 307
        # redirect to the canonical slash form so the client retries
        # with the same method + body. We deliberately do NOT internally
        # re-call `call_next` here — `BaseHTTPMiddleware` cannot be
        # invoked twice on the same scope (the first call's receive
        # stream is closed), and doing so manifests as
        # `anyio.ClosedResourceError` wrapped in `AssertionError` and
        # surfaces to clients as a generic 500.
        if response.status_code == 405 and not request.url.path.endswith("/"):
            redirect_target = request.url.path + "/"
            if request.url.query:
                redirect_target = f"{redirect_target}?{request.url.query}"
            return RedirectResponse(
                url=redirect_target,
                status_code=307,
                headers=get_cors_headers(request),
            )

        return response
    except Exception:
        logger.exception(
            "middleware caught unhandled error for %s %s", request.method, request.url
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "status_code": 500},
            headers=get_cors_headers(request),
        )


@app.options("/{rest_of_path:path}")
async def preflight_handler(request):
    return JSONResponse(content={"status": "ok"}, headers=get_cors_headers(request))


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(backups.router, prefix="/api")
app.include_router(ebay.router, prefix="/api")
app.include_router(facebook.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(vision.router, prefix="/api")
app.include_router(pricing.router, prefix="/api")
app.include_router(llm_config.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "3.1.0"}


def get_cors_headers(request):
    origin = request.headers.get("origin")
    if origin in CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": ", ".join(CORS_ALLOW_METHODS),
            "Access-Control-Allow-Headers": ", ".join(CORS_ALLOW_HEADERS),
            "Access-Control-Expose-Headers": "Content-Type, Content-Disposition, Authorization",
        }
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
        headers=get_cors_headers(request),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception("unhandled exception on %s %s", request.method, request.url)

    if settings.DEBUG:
        content = {
            "detail": str(exc),
            "type": type(exc).__name__,
            "stack_trace": traceback.format_exc().splitlines(),
            "status_code": 500,
        }
    else:
        content = {"detail": "Internal server error", "status_code": 500}

    return JSONResponse(
        status_code=500, content=content, headers=get_cors_headers(request)
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=27182)
