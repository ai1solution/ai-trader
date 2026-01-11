from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from api.routers import v4, analysis, legacy, market, analytics

app = FastAPI(
    title="AI Trader Unified API",
    description="Unified API for accessing V4, V3, and analysis tools.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(v4.router)
app.include_router(analysis.router)
app.include_router(legacy.router)
app.include_router(market.router)
app.include_router(analytics.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "AI Trader API is running"}

# Mount frontend as static files (must be last to allow API routes to match first)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
