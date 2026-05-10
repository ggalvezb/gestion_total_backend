"""Iniciar servidor: uvicorn app.main:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.database import connect_db, close_db
from app.core.config import get_settings
from app.routers import auth, cotizaciones, compras, documentos, costos_fijos, usuarios

settings = get_settings()

app = FastAPI(
    title="Abastecimiento Total API",
    description="Sistema de cotización y gestión de compras",
    version="1.0.0",
    redirect_slashes=False,
)

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lifecycle ──────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_db()
    # Crear carpeta de uploads si no existe
    Path(settings.storage_local_path).mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def shutdown():
    await close_db()

# ── Routers ────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api")
app.include_router(cotizaciones.router,  prefix="/api")
app.include_router(compras.router,       prefix="/api")
app.include_router(documentos.router,    prefix="/api")
app.include_router(costos_fijos.router,  prefix="/api")
app.include_router(usuarios.router,      prefix="/api")

# Servir archivos estáticos (uploads locales)
uploads_path = Path(settings.storage_local_path)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/api/files", StaticFiles(directory=str(uploads_path)), name="files")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
