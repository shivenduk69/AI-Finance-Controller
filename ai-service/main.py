import time
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router
from app.core.rabbitmq import rabbitmq_worker

app = FastAPI(
    title="AI Finance Controller — AI & Data Processing Service",
    description="Dedicated mathematical, reconciliation, forecasting, tax compliance, and RAG intelligence engine.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    rabbitmq_worker.start_consumer_thread()

@app.on_event("shutdown")
def shutdown_event():
    rabbitmq_worker.close()

# Internal CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/internal/health")
def healthcheck():
    """Healthcheck endpoint for Docker container and orchestrator probing."""
    return {
        "status": "ok",
        "service": "ai-service",
        "environment": settings.ENVIRONMENT,
        "timestamp": int(time.time())
    }

# Mount internal service endpoints
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=(settings.ENVIRONMENT == "development"))
