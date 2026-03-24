import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "etf_compositions.db")

# CORS: space-separated list of allowed origins via env var in production
# e.g. ALLOWED_ORIGINS="https://myapp.vercel.app https://myapp.netlify.app"
_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
PROD_ORIGINS = [o.strip() for o in _env_origins.split() if o.strip()]

DEV_ORIGINS = [
    "http://localhost:8003",
    "http://localhost:3000",
    "http://127.0.0.1:8003",
    "http://127.0.0.1:3000",
]

IS_PRODUCTION = os.environ.get("ENV") == "production"
ALLOWED_ORIGINS = PROD_ORIGINS if IS_PRODUCTION else DEV_ORIGINS
