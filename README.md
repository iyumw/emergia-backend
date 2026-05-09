# EmergyCalc Backend

Python/FastAPI backend for emergy calculation based on H.T. Odum's theory.

## Project Structure

```
emergy/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Ponto de entrada da API
│   ├── domain/                     # Regras de negócio puras (sem dependências externas)
│   │   ├── __init__.py
│   │   ├── entities.py             # Classes: Processo, Fluxo, Matriz, Grafo
│   │   └── algebra.py              # Classe: AlgebraEmergetica (regras de cálculo)
│   ├── application/                # Orquestração dos casos de uso
│   │   ├── __init__.py
│   │   └── calculador_service.py   # Classe: CalculadorEmergia
│   └── infrastructure/             # Comunicação com o mundo externo (Web, Arquivos)
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py           # Controladores (Endpoints REST para o Angular)
│       └── adapters/
│           ├── __init__.py
│           └── importador.py       # Classe: Importador (leitura e validação de arquivos)
├── requirements.txt                # Lista de dependências (como o package.json)
└── .gitignore
```

## Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the API
uvicorn main:app --reload --port 8000

# 4. Run tests
pytest tests/ -v
```

Open http://localhost:8000/docs for interactive Swagger documentation.

## Endpoints

| Method | Route            | Description                          |
|--------|------------------|--------------------------------------|
| POST   | /api/v1/calculate | Calculate emergy from JSON input     |
| POST   | /api/v1/import    | Calculate emergy from 3 CSV files    |
| POST   | /api/v1/export    | Calculate and download result as JSON|

## Example payload for `/api/v1/calculate`

# Motor de Cálculo Emergético (backend)

Projeto Python com FastAPI que implementa um motor de cálculo emergético baseado nas regras de H.T. Odum.

Este repositório contém a API que recebe a descrição de um sistema (fontes, processos e fluxos) e retorna a "emergia" distribuída entre os nós seguindo as quatro regras de álgebra emergética.

## Visão geral da estrutura

```
.
├── app/                        # Código da aplicação (API, domínio e infra)
│   ├── main.py                 # Ponto de entrada (FastAPI)
│   ├── application/            # Casos de uso / orquestração
│   ├── domain/                 # Regras de negócio (modelos e álgebra)
│   └── infrastructure/         # Adaptadores e rotas da API
├── tests/                      # Testes automatizados (pytest)
└── requirements.txt            # Dependências do projeto
```

## Conteúdo principal

- `app/main.py`: cria a instância FastAPI, configura CORS e registra as rotas em `app.infrastructure.api.routes`.
- `app/application/` e `app/domain/`: implementam a lógica de cálculo emergético e modelos Pydantic usados nos testes.
- `app/infrastructure/adapters/importador.py`: funções para parsear CSVs (usadas nos testes de integração).

## Requisitos

Recomendado: Python 3.10+.

As dependências estão listadas em `requirements.txt`.

## Instalação e execução (Windows)

Abra um terminal PowerShell e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Iniciar a API (a partir da raiz do projeto)
uvicorn app.main:app --reload --port 8000
```

Observação: se estiver usando cmd.exe, ative o venv com `.\.venv\Scripts\activate.bat`.

Após iniciar, a documentação interativa estará em: http://localhost:8000/docs

## Endpoints (resumo)

- GET  /                — Health check
- POST /api/v1/calculate — Recebe JSON com fontes/processos/fluxos e retorna o cálculo emergético
- POST /api/v1/import    — Importa dados via CSV (nodes, sources, edges)
- POST /api/v1/export    — (planejado) exporta resultados como arquivo

As rotas ficam registradas com prefixo `/api` (veja `app/main.py`). A documentação Swagger mostra os detalhes de payload.

## Executar testes

Os testes usam `pytest`. Execute no PowerShell:

```powershell
# Ative o ambiente virtual (veja seção anterior)
pip install -r requirements.txt
pytest tests/ -v
```

## Exemplos de payload

Exemplo de JSON para `/api/v1/calculate` (simplificado):

```json
{
  "sources": [
    { "id": "SRC_SUN", "label": "Sol", "uev": 1.0, "categoria": "renovavel", "quantidade": 3500000.0 }
  ],
  "processes": [
    { "id": "P1", "label": "Plantacao" },
    { "id": "P2", "label": "Colheita" }
  ],
  "flows": [
    { "origem": "SRC_SUN", "destino": "P1", "quantidade": 3500000.0 },
    { "origem": "P1", "destino": "P2", "quantidade": 1000.0 }
  ]
}
```

## Observações de segurança e produção

- Em desenvolvimento, o CORS permite `http://localhost:4200` e `http://localhost:3000` por padrão. Em produção, defina a variável de ambiente `ALLOWED_ORIGINS` com as URLs permitidas e evite `"*"`.
- Atualmente os dados são processados apenas em memória; não há persistência nem envio para serviços externos.