import pytest
import time
from app.infrastructure.adapters.graph_store import get_graph, save_graph
from app.infrastructure.adapters.graph_store import (
    save_graph,
    get_graph,
    SESSION_TTL_SECONDS,
    _store,
)


class TestGraphStore:

    def test_save_and_retrieve_graph(self):
        nodes = [{"id": "n1", "label": "Sun", "type": "source"}]
        edges = [{"id": "e1", "source": "n1", "target": "n2", "amount": 100}]
        result = {"total_emergy": 100.0, "unit": "sej"}
        gid = save_graph(nodes, edges, result)
        graph = get_graph(gid)
        assert graph is not None
        assert graph["graph_id"] == gid
        assert graph["nodes"] == nodes
        assert graph["edges"] == edges
        assert graph["result"] == result

    def test_get_nonexistent_graph_returns_none(self):
        assert get_graph("00000000-0000-0000-0000-000000000000") is None

    def test_expired_graph_returns_none(self):
        """A graph whose created_at is past TTL must be treated as expired."""
        nodes = [{"id": "n1", "label": "Sun", "type": "source"}]
        edges = [{"id": "e1", "source": "n1", "target": "n2", "amount": 100}]
        result = {"total_emergy": 100.0, "unit": "sej"}
        gid = save_graph(nodes, edges, result)

        import app.infrastructure.adapters.graph_store as store_mod
        past = time.time() - SESSION_TTL_SECONDS - 1
        store_mod._store[gid]["created_at"] = past

        assert get_graph(gid) is None

    def test_multiple_graphs_are_independent(self):
        n = [{"id": "n1", "label": "Sun", "type": "source"}]
        e = [{"id": "e1", "source": "n1", "target": "n2", "amount": 100}]
        r1 = {"total_emergy": 100.0, "unit": "sej"}
        r2 = {"total_emergy": 999.0, "unit": "sej"}
        gid1 = save_graph(n, e, r1)
        gid2 = save_graph(n, e, r2)
        assert gid1 != gid2
        assert get_graph(gid1)["result"]["total_emergy"] == 100.0
        assert get_graph(gid2)["result"]["total_emergy"] == 999.0

    @pytest.fixture(autouse=True)
    def clean_store(self):
        """Fixture para limpeza de estado antes e depois de cada teste.
        
        Usa yield para garantir que a limpeza ocorra mesmo se o teste falhar.
        Isso é importante para evitar deixar "lixo" que pode afetar outros testes.
        Se a implementação mudar para Redis/SQLite, essa fixture pode ser facilmente
        adaptada sem alterar os testes.
        """
        initial_store_state = dict(_store)
        try:
            yield
        finally:
            _store.clear()
            _store.update(initial_store_state)
