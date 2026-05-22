# Emergia Backend

Backend do projeto **ESCALE** - Sistema de cálculo e análise de emergia com visualização ambiental.

## 📋 Descrição

Motor de cálculo emergético que recebe a descrição de um sistema (fontes, processos e fluxos) e distribui a "emergia" entre os nós seguindo as regras de álgebra emergética de Odum. Este projeto foi desenvolvido como trabalho acadêmico com foco em modelagem de fluxos de emergia, visualização de grafos ambientais e manipulação de inventários de ciclo de vida (LCI).

## ✨ Características

- **Modelagem de fluxos de emergia** baseada em teoria estabelecida (H.T. Odum)
- **Visualização de grafos ambientais** para representação de processos e fluxos energéticos
- **Manipulação de inventários de ciclo de vida (LCI)** para análise de sustentabilidade
- **API REST** documentada com Swagger/OpenAPI
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
│   │   ├── glossary.py         # Dicionário de termos
│   │   └── exceptions.py       # Exceções customizadas
│   └── infrastructure/         # Comunicação externa (API, Arquivos)
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py       # Endpoints REST
│       └── adapters/
│           ├── __init__.py
│           ├── graph_store.py  # Armazenamento e visualização de grafos
│           └── importador.py   # Leitura e validação de LCI e outros arquivos
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
cd emergia-backend
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

### 1. **POST `/calculate`** - Cálculo de Emergia a partir de JSON

Recebe nós e arestas como JSON e retorna a emergia total do sistema.

**Parâmetros do Request Body:**
```json
{
  "nodes": [
    {
      "id": "SUN_01",
      "label": "Solar Energy",
      "type": "source",
      "uev": 1.0,
      "category": "renewable",
      "amount": 3500000.0
    },
    { "id": "P1", "label": "Plantation", "type": "process" },
    { "id": "P2", "label": "Harvest", "type": "process" }
  ],
  "edges": [
    { "source": "SUN_01", "target": "P1", "amount": 3500000.0, "unit": "sej" },
    { "source": "P1", "target": "P2", "amount": 1000.0, "unit": "kg" }
  ]
}
```

**Resposta:** Objeto com resultado do cálculo emergético.

---

### 2. **POST `/import`** - Importação de Dados (CSV, JSON, XLSX)

Importa dados a partir de arquivos e realiza o cálculo automaticamente.

**Entrada:** 
- Um arquivo (.json, .xlsx) ou
- Três arquivos CSV separados (nodes, sources, edges)

**Resposta:**
```json
{
  "graph_id": "abc123def456",
  "expires_in_seconds": 3600
}
```

---

### 3. **GET `/graph/{graph_id}`** - Recuperar Grafo

Retorna o grafo completo e os resultados dos cálculos para um ID específico.
Grafos expiram após 1 hora e são removidos automaticamente.

**Resposta:**
```json
{
  "graph_id": "abc123def456",
  "created_at": "2024-05-22T10:30:00Z",
  "nodes": [...],
  "edges": [...],
  "result": {
    "total_emergy": 4500000.0,
    "unit": "sej",
    "stats": {
      "nodes_count": 3,
      "edges_count": 2,
      "processing_time_ms": 45
    }
  }
}
```

---

### 4. **POST `/export/pdf`** - Exportar Relatório em PDF

Gera um PDF customizável incluindo a captura visual do grafo.

**Parâmetros do Request Body:**
```json
{
  "graph_id": "abc123def456",
  "config": {
    "title": "Análise de Sistema de Silagem",
    "graph_image": "data:image/png;base64,iVBORw0KGgo...",
    "show_stats": true
  }
}
```

**Resposta:** PDF para download.

---

### 5. **GET `/glossary`** - Glossário de Termos

Retorna o dicionário de conceitos de emergia e referências metodológicas.

**Resposta:** Objeto com definições e termos-chave da análise emergética.

## 🧪 Executar Testes

```bash
# Todos os testes com cobertura
pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=80

# Apenas um arquivo
pytest tests/test_calculator.py -v

# Com saída detalhada
pytest tests/ -vv --tb=short
```

## 📝 Notas Importantes

- Os dados são processados **apenas em memória**; sem persistência em banco de dados
- A arquitetura segue **Clean Architecture** com separação clara entre domínio, aplicação e infraestrutura
- Testes cobrem unidades, integração e performance

## 📚 Referências

- [H.T. Odum - Emergy Theory](https://www.energy.usf.edu/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
