# Emergia Backend

API FastAPI para cálculo de emergia baseada na teoria de H.T. Odum.

## 📋 Descrição

Motor de cálculo emergético que recebe a descrição de um sistema (fontes, processos e fluxos) e distribui a "emergia" entre os nós seguindo as regras de álgebra emergética de Odum.

## ✨ Características

- **API REST** documentada com Swagger/OpenAPI
- **Cálculo de Emergia** baseado em teoria estabelecida
- **Importação de CSV** para dados em lote
- **Arquitetura em camadas**: Domain, Application, Infrastructure
- **Testes automatizados** com cobertura mínima de 80%
- **CORS configurável** para desenvolvimento e produção

## 📁 Estrutura do Projeto

```
emergia-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Ponto de entrada da API (FastAPI)
│   ├── application/
│   │   ├── __init__.py
│   │   └── emergy_calculator.py   # Orquestração de casos de uso
│   ├── domain/                 # Lógica de negócio (pura, sem dependências externas)
│   │   ├── __init__.py
│   │   ├── entities.py         # Modelos: Processo, Fluxo, Grafo, etc
│   │   ├── algebra.py          # Regras de cálculo emergético
│   │   ├── graph_store.py      # Armazenamento e manipulação do grafo
│   │   ├── glossary.py         # Dicionário de termos
│   │   └── exceptions.py       # Exceções customizadas
│   └── infrastructure/         # Comunicação externa (API, Arquivos)
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py       # Endpoints REST
│       └── adapters/
│           ├── __init__.py
│           └── importador.py   # Leitura e validação de arquivos importados
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Configuração do pytest
│   ├── helpers.py              # Utilitários para testes
│   ├── test_*.py               # Testes unitários e de integração
│   └── (fixtures e mocks)
├── requirements.txt            # Dependências
└── README.md
```

## 🔧 Requisitos

- **Python**: 3.10+
- **pip**: Gerenciador de pacotes

## 🚀 Instalação e Execução

### 1. Clonar o repositório e entrar no diretório

```bash
git clone <repositorio>
cd emergia_backend
```

### 2. Criar e ativar ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd.exe):**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Executar a API

```bash
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`  
Documentação interativa (Swagger): `http://localhost:8000/docs`

## 🔌 Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Health check |
| POST | `/api/v1/calculate` | Calcula emergia a partir de JSON |
| POST | `/api/v1/import` | Importa e calcula emergia a partir de CSV |

### Exemplo de payload para `/api/v1/calculate`

```json
{
  "sources": [
    {
      "id": "SUN",
      "label": "Solar",
      "uev": 1.0,
      "categoria": "renovavel",
      "quantidade": 3500000.0
    }
  ],
  "processes": [
    { "id": "P1", "label": "Fotossíntese" },
    { "id": "P2", "label": "Crescimento" }
  ],
  "flows": [
    { "origem": "SUN", "destino": "P1", "quantidade": 3500000.0 },
    { "origem": "P1", "destino": "P2", "quantidade": 1000.0 }
  ]
}
```

## 🧪 Executar Testes

```bash
# Todos os testes com cobertura
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

# Apenas um arquivo
pytest tests/test_calculator.py -v

# Com saída detalhada
pytest tests/ -vv --tb=short
```

## 📦 Dependências Principais

Veja `requirements.txt` para a lista completa. Principais:

- **FastAPI**: Framework web assíncrono
- **Pydantic**: Validação de dados e serialização
- **pytest**: Framework de testes
- **pytest-cov**: Cobertura de testes

## ⚙️ Configuração

### CORS em Desenvolvimento

Por padrão, CORS permite requisições de `http://localhost:4200` (Angular) e `http://localhost:3000` (Node).

Para alterar, edite `app/main.py` ou defina a variável de ambiente `ALLOWED_ORIGINS`:

```bash
set ALLOWED_ORIGINS=http://localhost:3000,http://meuapp.local
```

## 📝 Notas Importantes

- Os dados são processados **apenas em memória**; sem persistência em banco de dados
- A arquitetura segue **Clean Architecture** com separação clara entre domínio, aplicação e infraestrutura
- Testes cobrem unidades, integração e performance

## 📚 Referências

- [H.T. Odum - Emergy Theory](https://www.energy.usf.edu/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)