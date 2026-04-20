import logging
import os
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import analytics, auth, backups, ebay, images, items
from .settings import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

UPLOAD_DIR = str(settings.upload_path)
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info("upload directory: %s", UPLOAD_DIR)

app = FastAPI(
    title="WHIS - Whole-Home Inventory System",
    description="A self-hosted platform for managing household inventories",
    version="2.0.0",
    redirect_slashes=False,
)


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
    expose_headers=["Content-Type", "Content-Disposition", "Authorization"],
    max_age=3600,
)


@app.middleware("http")
async def add_cors_and_trailing_slash(request, call_next):
    try:
        response = await call_next(request)
        response.headers.update(get_cors_headers(request))

        if response.status_code == 405 and not request.url.path.endswith("/"):
            request.scope["path"] = request.url.path + "/"
            response = await call_next(request)
            response.headers.update(get_cors_headers(request))

        return response
    except Exception:
        logger.exception("middleware caught unhandled error for %s %s", request.method, request.url)
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


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

    return JSONResponse(status_code=500, content=content, headers=get_cors_headers(request))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=27182)
