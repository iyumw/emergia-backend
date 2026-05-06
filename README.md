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

```json
{
  "sources": [
    { "id": "SRC_SUN", "name": "Solar Energy", "uev": 1.0, "category": "renewable", "amount": 3.5e14 }
  ],
  "processes": [
    { "id": "P1", "name": "Cultivation" },
    { "id": "P2", "name": "Harvest" }
  ],
  "flows": [
    { "source_id": "SRC_SUN", "target_id": "P1", "amount": 3.5e14, "unit": "sej" },
    { "source_id": "P1",      "target_id": "P2", "amount": 1000,   "unit": "kg"  }
  ]
}
```

## Angular integration

The API is already configured with CORS for `http://localhost:4200`. (still has to be deployed)
Point your Angular `HttpClient` to `http://localhost:8000/api/v1`.