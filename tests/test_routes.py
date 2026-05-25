import time
from fastapi.testclient import TestClient
from app.main import app 

client = TestClient(app)

def test_get_glossary_route():
    """Garante cobertura para a rota do glossário (GET /api/glossary)."""
    response = client.get("/api/glossary")  
    assert response.status_code == 200
    assert "categorias" in response.json()


def test_import_data_route():
    """Cobre a rota de importação garantindo que ela passa pelas validações iniciais."""
    payload = {"nodes": [{"id": "N1"}], "edges": []}
    response = client.post("/api/import", json=payload)
    assert response.status_code == 422


def test_get_graph_by_id_not_found():
    """Testa o bloco 'if not graph' dentro da rota GET /api/graph/{graph_id} (Retorno 404)."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/graph/{fake_id}")
    assert response.status_code == 404


def test_get_graph_by_id_success_via_store_injection():
    """Força a execução de todas as linhas de sucesso internas do GET /api/graph/{graph_id}."""
    # Importamos o dicionário em memória usado pelo backend para injetar um estado válido direto nele
    from app.infrastructure.adapters.graph_store import _store  
    
    graph_id = "session-mock-cobertura"
    
    _store[graph_id] = {
        "graph_id": graph_id,
        "created_at": time.time(),
        "nodes": [{"id": "N1", "label": "Sol", "type": "source", "uev": 1.0}],
        "edges": [],
        "result": {
            "total_emergy": 1000.0,
            "unit": "sej",
            "stats": {"nodes_count": 1, "edges_count": 0, "execution_time_ms": 1.5}
        }
    }
    
    response = client.get(f"/api/graph/{graph_id}")
    assert response.status_code == 200
    assert response.json()["graph_id"] == graph_id