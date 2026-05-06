from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.api.routes import router

app = FastAPI(title="Motor de Cálculo Emergético", version="1.0.0")

# Configuração de CORS para permitir requisições do Angular (geralmente localhost:4200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Na produção, coloque a URL exata do seu front-end
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra as rotas
app.include_router(router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "Software de Emergia Operacional"}