from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from . import models, database
from .routers import auth, items, images, analytics, backups

# Create the uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join("backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="WHIS - Whole-Home Inventory System",
    description="A self-hosted platform for managing household inventories",
    version="1.0.0",
    # Don't redirect slashes to maintain URL consistency
    redirect_slashes=False
)

# Add exception handler for 405 Method Not Allowed
@app.exception_handler(405)
async def method_not_allowed_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=405,
        content={"detail": "Method not allowed"},
        headers=get_cors_headers(request)
    )

# Get CORS origins from environment variable, default to development server
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Type", "Content-Disposition"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Add middleware to handle trailing slashes and ensure CORS headers
@app.middleware("http")
async def add_cors_and_trailing_slash(request, call_next):
    try:
        response = await call_next(request)
        
        # Add CORS headers to all responses
        response.headers.update(get_cors_headers(request))
        
        # Handle trailing slashes
        if response.status_code == 405 and not request.url.path.endswith('/'):
            request.scope['path'] = request.url.path + '/'
            response = await call_next(request)
            response.headers.update(get_cors_headers(request))
        
        return response
    except Exception as e:
        from fastapi.responses import JSONResponse
        import traceback
        print(f"Middleware caught error: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "status_code": 500
            },
            headers=get_cors_headers(request)
        )

# Add OPTIONS handler for preflight requests
@app.options("/{rest_of_path:path}")
async def preflight_handler():
    return {"status": "ok"}

# Mount static file directory for uploaded images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(backups.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Common CORS headers for error responses
def get_cors_headers(request):
    origin = request.headers.get("origin", CORS_ORIGINS[0])
    if origin in CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Expose-Headers": "Content-Type, Content-Disposition"
        }
    return {}

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        },
        headers=get_cors_headers(request)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    import traceback
    import sys
    
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Print detailed error information
    print("\n=== Error Details ===")
    print(f"Request URL: {request.url}")
    print(f"Request Method: {request.method}")
    print(f"Exception Type: {exc_type.__name__}")
    print(f"Exception Message: {str(exc)}")
    print("\n=== Full Traceback ===")
    print(traceback.format_exc())
    
    # Get the full stack trace
    stack_summary = traceback.extract_tb(exc_traceback)
    formatted_stack = []
    for frame in stack_summary:
        formatted_stack.append({
            'filename': frame.filename,
            'line': frame.lineno,
            'function': frame.name,
            'code': frame.line
        })
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": exc_type.__name__,
            "stack_trace": formatted_stack,
            "status_code": 500
        },
        headers=get_cors_headers(request)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=27182)
