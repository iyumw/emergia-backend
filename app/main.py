"""
Entry point for the FastAPI application — Emergy Calculation Engine.

Security (RNF 3.1.7):
  - Data is processed only in memory, without persistence in databases
    or sending to external servers.
  - In production, replace allow_origins=["*"] with the exact URL of the frontend
    para evitar acesso não autorizado (ex.: ["https://meu-app.com"]).
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.api.routes import router

app = FastAPI(
    title="Motor de Cálculo Emergético",
    version="1.0.0",
    description=(
        "API para cálculo de emergia baseado nas 4 regras de álgebra emergética de H.T. Odum. "
        "Todos os dados são processados localmente em memória, sem persistência externa."
    ),
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# On Render (production), ALLOWED_ORIGINS env var is set to the frontend URL.
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = (
    [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    if _allowed_origins_env
    else ["http://localhost:4200", "http://localhost:3000"]  # desenvolvimento local
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

# ── Rotas ─────────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api")


@app.get("/", tags=["Health"])
def health_check():
    """Verifica se a aplicação está operacional."""
    return {"status": "Software de Emergia Operacional", "version": "1.0.0"}