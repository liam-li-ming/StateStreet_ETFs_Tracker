from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import ALLOWED_ORIGINS
from backend.database import init_db
from backend.routers import etfs, compositions, alerts, search, pipeline, dividends


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="StateStreet ETF Tracker",
    description="API for tracking SSGA ETF compositions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(etfs.router)
app.include_router(compositions.router)
app.include_router(alerts.router)
app.include_router(search.router)
app.include_router(pipeline.router)
app.include_router(dividends.router)


@app.get("/")
def root():
    return {"message": "StateStreet ETF Tracker API", "docs": "/docs"}
