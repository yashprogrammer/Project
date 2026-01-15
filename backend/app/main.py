from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from app.database import connect_to_mongo, close_mongo_connection
from app.routers import stream, departments

# Configure logger
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Sens-AI MVP backend...")
    await connect_to_mongo()
    yield
    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_mongo_connection()


app = FastAPI(
    title="Sens-AI MVP API",
    description="MVP version of Sens-AI voice bot with RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS setup
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://frontend:80",  # Docker internal network
    "http://proj3-frontend:80",  # Docker container name
    "http://proj3-frontend-prod:80",  # Production container name
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stream.router, prefix="/api/v1/stream", tags=["Stream"])
app.include_router(departments.router, prefix="/api/v1/departments", tags=["Departments"])


@app.get("/")
def read_root():
    return {"message": "Sens-AI MVP API is running", "version": "0.1.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/vector-index")
def check_vector_index():
    """Check if vector search index exists and is active"""
    from app.services.vector_index_service import VectorIndexService
    
    service = VectorIndexService()
    result = service.verify_index_exists()
    
    if result.get("status") == "success" and result.get("active"):
        return {
            "status": "healthy",
            "vector_index": {
                "exists": True,
                "active": True,
                "index_name": result.get("index_name"),
                "message": result.get("message")
            }
        }
    else:
        return {
            "status": "unhealthy",
            "vector_index": {
                "exists": result.get("exists", False),
                "active": result.get("active", False),
                "index_name": result.get("index_name"),
                "message": result.get("message"),
                "instructions": service.get_creation_instructions() if result.get("status") == "not_found" else None
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

