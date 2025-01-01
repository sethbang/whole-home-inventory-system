from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from . import models, database
from .routers import auth, items, images, analytics, backups, ebay

# Create the uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join("/app", "backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
print(f"Upload directory path: {UPLOAD_DIR}")
print(f"Upload directory exists: {os.path.exists(UPLOAD_DIR)}")
print(f"Directory permissions: {oct(os.stat(UPLOAD_DIR).st_mode)[-3:]}")

# Ensure uploads directory is accessible
try:
    test_file = os.path.join(UPLOAD_DIR, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    print("Upload directory is writable")
except Exception as e:
    print(f"Error testing upload directory: {str(e)}")

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

# Get CORS settings from environment variables with defaults
# Default CORS origins support both HTTP and HTTPS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,https://localhost:5173,http://192.168.1.122:5173,https://192.168.1.122:5173").split(",")
CORS_ALLOW_METHODS = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH").split(",")
CORS_ALLOW_HEADERS = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization,Accept,Origin,X-Requested-With").split(",")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=["Content-Type", "Content-Disposition", "Authorization"],
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
async def preflight_handler(request):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={"status": "ok"},
        headers=get_cors_headers(request)
    )

# Mount static file directory for uploaded images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(backups.router, prefix="/api")
app.include_router(ebay.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Common CORS headers for error responses
def get_cors_headers(request):
    origin = request.headers.get("origin")
    if origin in CORS_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": ", ".join(CORS_ALLOW_METHODS),
            "Access-Control-Allow-Headers": ", ".join(CORS_ALLOW_HEADERS),
            "Access-Control-Expose-Headers": "Content-Type, Content-Disposition, Authorization"
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
