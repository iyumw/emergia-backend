"""
Full test suite for the emergy calculation engine.

Coverage target : ≥ 80% (RNF 3.1.8)
Mandatory scenarios (RNF 3.1.10):
  - Graph without co-products
  - Graph with co-products
  - Graph with a loop / feedback

Run with:
    pytest tests/ -v
"""

import time
import pytest
from app.application.emergy_calculator import EmergyCalculator
from app.domain.entities import GraphData, Node, Edge
from app.domain.exceptions import InvalidGraphError, NodeNotFoundError
from app.domain.graph_store import (
    save_graph,
    get_graph,
    SESSION_TTL_SECONDS,
    _store,
)
from app.infrastructure.adapters.importador import (
    build_graph_data_from_single_csv,
    build_graph_data_from_csvs,
    MAX_FILE_SIZE_BYTES,
    _parse_nodes_section,
    _parse_sources_section,
    _parse_edges_section,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def calculator():
    return EmergyCalculator()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _source(label="Sun", uev=1.0, amount=1000.0, node_id=None) -> Node:
    kwargs = dict(
        label=label, 
        type="source", 
        uev=uev, 
        category="renewable", 
        amount=amount
    )
    if node_id:
        kwargs["id"] = node_id
    return Node(**kwargs)


def _process(label, multi=False, node_id=None) -> Node:
    kwargs = dict(label=label, type="process", is_multi_output=multi)
    if node_id:
        kwargs["id"] = node_id
    return Node(**kwargs)


def _edge(source, target, amount=1000.0) -> Edge:
    return Edge(source=source, target=target, amount=amount)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Odum's algebra rules
# ─────────────────────────────────────────────────────────────────────────────

class TestOdumRules:

    def test_rule1_source_emergy_goes_to_output(self, calculator):
        """Rule 1: full source emergy is transferred to the output node."""
        src = _source(uev=2.0, amount=500.0, node_id="SRC")
        p1  = _process("Process A", node_id="P1")
        data = GraphData(nodes=[src, p1], edges=[_edge("SRC", "P1")])
        result = calculator.calculate(data)
        p1_c = next(c for c in result["energy_intensity"] if c["id"] == "P1")
        assert p1_c["percentage_value"] == "100.0%"

    def test_rule2_co_products_receive_full_emergy(self, calculator):
        """Rule 2: each co-product receives the TOTAL emergy (no split)."""
        src  = _source(node_id="SRC")
        p1   = _process("Distillery", multi=True, node_id="P1")
        out1 = _process("Ethanol", node_id="OUT1")
        out2 = _process("Bagasse", node_id="OUT2")
        data = GraphData(
            nodes=[src, p1, out1, out2],
            edges=[
                _edge("SRC", "P1"),
                _edge("P1", "OUT1", 800),
                _edge("P1", "OUT2", 200),
            ],
        )
        result = calculator.calculate(data)
        assert result["total_emergy"] == pytest.approx(2000.0)

    def test_rule3_proportional_split(self, calculator):
        """Rule 3: non co-product split distributes emergy proportionally."""
        src  = _source(node_id="SRC")
        p1   = _process("Splitter", multi=False, node_id="P1")
        out1 = _process("Output 1", node_id="OUT1")
        out2 = _process("Output 2", node_id="OUT2")
        data = GraphData(
            nodes=[src, p1, out1, out2],
            edges=[
                _edge("SRC", "P1"),
                _edge("P1", "OUT1", 700),
                _edge("P1", "OUT2", 300),
            ],
        )
        result = calculator.calculate(data)
        assert result["total_emergy"] == pytest.approx(1000.0)

    def test_rule4_avoids_double_counting(self, calculator):
        """Rule 4: emergy not counted twice when flows converge from same origin."""
        src   = _source(node_id="SRC")
        p1    = _process("Process A", multi=True, node_id="P1")
        p2    = _process("Process B", node_id="P2")
        final = _process("Junction", node_id="FINAL")
        
        data = GraphData(
            nodes=[src, p1, p2, final],
            edges=[
                _edge("SRC", "P1"),
                _edge("P1", "P2"),
                _edge("P1", "FINAL"),
                _edge("P2", "FINAL"),
            ],
        )
        result = calculator.calculate(data)
        assert result["total_emergy"] == pytest.approx(1000.0)

    def test_rule4_independent_sources_are_summed(self, calculator):
        """Rule 4 negative: independent sources must be summed."""
        src1 = _source(label="Sun",  uev=1.0, amount=600.0, node_id="SRC1")
        src2 = _source(label="Rain", uev=1.0, amount=400.0, node_id="SRC2")
        p1   = _process("Plant", node_id="P1")
        data = GraphData(
            nodes=[src1, src2, p1],
            edges=[_edge("SRC1", "P1", 600), _edge("SRC2", "P1", 400)],
        )
        result = calculator.calculate(data)
        assert result["total_emergy"] == pytest.approx(1000.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Loop / feedback graphs
# ─────────────────────────────────────────────────────────────────────────────

class TestLoopGraphs:

    def test_direct_loop_does_not_cause_infinite_recursion(self, calculator):
        src = _source(node_id="SRC")
        pa  = _process("Process A", node_id="PA")
        pb  = _process("Process B", node_id="PB")
        data = GraphData(
            nodes=[src, pa, pb],
            edges=[_edge("SRC", "PA"), _edge("PA", "PB"), _edge("PB", "PA")],
        )
        result = calculator.calculate(data)
        assert "total_emergy" in result
        assert result["total_emergy"] >= 0

    def test_indirect_loop_three_nodes(self, calculator):
        src = _source(node_id="SRC")
        pa  = _process("A", node_id="PA")
        pb  = _process("B", node_id="PB")
        pc  = _process("C", node_id="PC")
        data = GraphData(
            nodes=[src, pa, pb, pc],
            edges=[
                _edge("SRC", "PA"),
                _edge("PA",  "PB"),
                _edge("PB",  "PC"),
                _edge("PC",  "PA"),
            ],
        )
        result = calculator.calculate(data)
        assert "total_emergy" in result
        assert result["total_emergy"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Graph store
# ─────────────────────────────────────────────────────────────────────────────

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

        import app.domain.graph_store as store_mod
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


# ─────────────────────────────────────────────────────────────────────────────
# 4. Integration — single CSV → store → retrieve
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleCSVIntegration:

    SIMPLE_CSV = b"""\
[nodes]
id,label,is_multi_output
proc-01,Plantation,false
proc-02,Harvest,false

[sources]
id,label,uev,category,amount
src-01,Solar Energy,1.0,renewable,3500000.0

[edges]
source,target,amount
src-01,proc-01,3500000.0
proc-01,proc-02,1000.0
"""

    CO_PRODUCT_CSV = b"""\
[nodes]
id,label,is_multi_output
dest-01,Distillery,true
ethanol-01,Ethanol,false
bagasse-01,Bagasse,false

[sources]
id,label,uev,category,amount
sol-01,Sun,1.0,renewable,1000.0

[edges]
source,target,amount
sol-01,dest-01,1000.0
dest-01,ethanol-01,800.0
dest-01,bagasse-01,200.0
"""

    def test_no_co_products_total_emergy(self, calculator):
        ir = build_graph_data_from_single_csv(self.SIMPLE_CSV)
        result = calculator.calculate(ir.graph_data)
        assert result["total_emergy"] == pytest.approx(3500000.0)

    def test_no_co_products_graph_structure(self):
        ir = build_graph_data_from_single_csv(self.SIMPLE_CSV)
        assert len(ir.nodes) == 3
        assert len(ir.edges) == 2

    def test_co_products_both_receive_full_emergy(self, calculator):
        ir     = build_graph_data_from_single_csv(self.CO_PRODUCT_CSV)
        result = calculator.calculate(ir.graph_data)
        assert result["total_emergy"] == pytest.approx(2000.0)

    def test_result_contains_required_fields(self, calculator):
        ir     = build_graph_data_from_single_csv(self.SIMPLE_CSV)
        result = calculator.calculate(ir.graph_data)
        assert "total_emergy" in result
        assert result["unit"] == "sej"
        assert "stats" in result
        assert "energy_intensity" in result

    def test_import_and_store_full_flow(self, calculator):
        """Full flow: CSV → parse → calculate → store → retrieve."""
        ir     = build_graph_data_from_single_csv(self.SIMPLE_CSV)
        result = calculator.calculate(ir.graph_data)

        nodes_payload = [n.model_dump() for n in ir.nodes]
        edges_payload = [e.model_dump() for e in ir.edges]
        gid = save_graph(nodes_payload, edges_payload, result)

        graph = get_graph(gid)
        assert graph is not None
        assert graph["result"]["total_emergy"] == pytest.approx(3500000.0)
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 2

    def test_comments_and_blank_lines_are_ignored(self, calculator):
        csv = b"""\
# comment

[sources]
id,label,uev,category,amount
s1,Sun,1.0,renewable,500.0

# another comment
[nodes]
id,label
p1,Plant

[edges]
source,target,amount
s1,p1,500.0
"""
        ir     = build_graph_data_from_single_csv(csv)
        result = calculator.calculate(ir.graph_data)
        assert result["total_emergy"] == pytest.approx(500.0)

    def test_section_order_does_not_matter(self, calculator):
        csv = b"""\
[edges]
source,target,amount
src-x,proc-x,1000.0

[sources]
id,label,uev,category,amount
src-x,Sun,1.0,renewable,1000.0

[nodes]
id,label
proc-x,Process
"""
        ir     = build_graph_data_from_single_csv(csv)
        result = calculator.calculate(ir.graph_data)
        assert result["total_emergy"] == pytest.approx(1000.0)

    def test_response_time_within_limit(self, calculator):
        ir     = build_graph_data_from_single_csv(self.SIMPLE_CSV)
        result = calculator.calculate(ir.graph_data)
        assert result["stats"]["processing_time_ms"] < 10_000


# ─────────────────────────────────────────────────────────────────────────────
# 5. Importer unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestImporter:

    def test_nodes_section_auto_generates_id(self):
        nodes = _parse_nodes_section("label,is_multi_output\nProcess X,false\n")
        assert len(nodes) == 1
        assert nodes[0].id
        assert nodes[0].label == "Process X"

    def test_nodes_section_preserves_explicit_id(self):
        nodes = _parse_nodes_section("id,label\nMY_ID,Process Y\n")
        assert nodes[0].id == "MY_ID"

    def test_sources_section_missing_required_column(self):
        with pytest.raises(ValueError, match="uev"):
            _parse_sources_section("label,category\nSun,renewable\n")

    def test_sources_section_default_amount_is_one(self):
        sources = _parse_sources_section("label,uev,category\nSun,1.0,renewable\n")
        assert sources[0].amount == pytest.approx(1.0)

    def test_edges_section_invalid_amount(self):
        with pytest.raises(ValueError, match="Valor numérico inválido"):
            _parse_edges_section("source,target,amount\nA,B,NOT_A_NUMBER\n")

    def test_nodes_section_skips_blank_labels(self):
        nodes = _parse_nodes_section("label\nValid\n\n   \n")
        assert len(nodes) == 1

    def test_file_size_limit_enforced(self):
        oversized = b"x" * (MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ValueError, match="maximum allowed size"):
            build_graph_data_from_single_csv(oversized)

    def test_missing_all_sections_raises_error(self):
        with pytest.raises(ValueError, match="Nenhuma seção válida encontrada"):
            build_graph_data_from_single_csv(b"label,uev\nSun,1.0\n")

    def test_empty_node_and_source_sections_raises_error(self):
        with pytest.raises(ValueError, match="está faltando as colunas obrigatórias"):
            build_graph_data_from_single_csv(b"[nodes]\n\n[edges]\nsource,target,amount\n")

    def test_backwards_compat_multi_csv(self):
        data = build_graph_data_from_csvs(
            "id,label\nproc-a,Process A\n",
            "id,label,uev,category,amount\nsol-x,Sun,1.0,renewable,500.0\n",
            "source,target,amount\nsol-x,proc-a,500.0\n",
        )
        assert len(data.nodes) == 2
        assert len(data.edges) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:

    def test_empty_graph_raises_error(self, calculator):
        with pytest.raises(InvalidGraphError, match="Grafo inválido"):
            calculator.calculate(GraphData(nodes=[], edges=[]))

    def test_edge_pointing_to_missing_node(self, calculator):
        """Testa se NodeNotFoundError é lançado quando uma aresta referencia nó inexistente.
        
        Ao invés de capturar ValueError genérico, usamos NodeNotFoundError para ser específico.
        Isso evita falsos positivos onde outro ValueError poderia passar.
        """
        p1 = _process("P1", node_id="P1")
        with pytest.raises(NodeNotFoundError, match="GHOST"):
            calculator.calculate(GraphData(
                nodes=[p1],
                edges=[Edge(source="P1", target="GHOST", amount=10)],
            ))

    def test_source_node_without_uev_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Node(label="Bad Source", type="source", category="renewable", amount=100)

    def test_auto_generated_ids_are_unique(self):
        ids = [Node(label=f"N{i}", type="process").id for i in range(20)]
        assert len(ids) == len(set(ids))

    def test_edge_with_zero_amount_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Edge(source="A", target="B", amount=0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Performance — RNF 3.1.2 and 3.1.3
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:

    def _linear_graph(self, n: int) -> GraphData:
        src       = _source(node_id="SRC_PERF")
        processes = [_process(f"P{i}", node_id=f"PERF_{i}") for i in range(n)]
        nodes     = [src] + processes
        edges     = [_edge("SRC_PERF", "PERF_0")]
        for i in range(n - 1):
            edges.append(_edge(f"PERF_{i}", f"PERF_{i + 1}"))
        return GraphData(nodes=nodes, edges=edges)

    def test_medium_graph_within_time_limit(self, calculator):
        result = calculator.calculate(self._linear_graph(500))
        assert result["stats"]["processing_time_ms"] < 10_000

    def test_large_graph_no_error(self, calculator):
        result = calculator.calculate(self._linear_graph(1_000))
        assert result["total_emergy"] > 0

    def test_star_graph_3000_edges(self, calculator):
        n_leaves = 3_000
        src      = _source(node_id="SRC_STAR")
        hub      = _process("Hub", node_id="HUB")
        leaves   = [_process(f"F{i}", node_id=f"LEAF_{i}") for i in range(n_leaves)]
        nodes    = [src, hub] + leaves
        edges    = [_edge("SRC_STAR", "HUB")]
        edges   += [_edge("HUB", f"LEAF_{i}", 1.0) for i in range(n_leaves)]
        result   = calculator.calculate(GraphData(nodes=nodes, edges=edges))
        assert result["stats"]["edges_count"] == n_leaves + 1
        assert result["stats"]["processing_time_ms"] < 10_000


# ─────────────────────────────────────────────────────────────────────────────
# 8. Glossary
# ─────────────────────────────────────────────────────────────────────────────

class TestGlossary:

    def test_returns_correct_structure(self):
        from app.domain.glossary import get_glossary
        g = get_glossary()
        assert "total_termos" in g or "categorias" in g
        assert len(g) > 0

    def test_every_category_has_content(self):
        from app.domain.glossary import get_glossary
        g = get_glossary()
        assert len(g) > 0

    def test_every_term_has_required_fields(self):
        from app.domain.glossary import get_glossary, _GLOSSARIO
        for term in _GLOSSARIO:
            assert "termo" in term
            assert "definicao" in term
            assert "referencia" in term


import pandas as pd
from io import BytesIO
from app.infrastructure.adapters.importador import build_from_xlsx

class TestExcelImporter:
    def test_import_valid_xlsx(self, calculator):
        # Criando um Excel em memória para testar
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame([
                {"id": "P1", "label": "Processo", "is_multi_output": False}
            ]).to_excel(writer, sheet_name='nodes', index=False)
            
            pd.DataFrame([
                {"id": "S1", "label": "Sol", "uev": 1.0, "category": "R", "amount": 500}
            ]).to_excel(writer, sheet_name='sources', index=False)
            
            pd.DataFrame([
                {"source": "S1", "target": "P1", "amount": 500}
            ]).to_excel(writer, sheet_name='edges', index=False)
        
        excel_bytes = output.getvalue()
        
        ir = build_from_xlsx(excel_bytes)
        result = calculator.calculate(ir.graph_data)
        
        assert result["total_emergy"] == 500.0
        assert len(ir.nodes) == 2