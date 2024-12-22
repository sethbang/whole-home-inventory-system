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
    version="1.0.0"
)

# Configure CORS for development and preview
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite development server
        "http://localhost:4173",  # Vite preview server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "detail": exc.detail,
        "status_code": exc.status_code
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
