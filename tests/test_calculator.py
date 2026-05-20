import pytest
from app.domain.entities import GraphData
from tests.helpers import _source, _process, _edge

# ─────────────────────────────────────────────────────────────────────────────
# 1. Odum's algebra rules
# ─────────────────────────────────────────────────────────────────────────────

class TestOdumRules:

    def test_rule1_source_emergy_goes_to_output(self, calculator):
        """Rule 1: full source emergy is transferred to the output node."""
        src = _source("Solar",uev=2.0, amount=1000.0, node_id="SRC")
        p1  = _process("Process A", node_id="P1")
        data = GraphData(nodes=[src, p1], edges=[_edge("SRC", "P1")])
        result = calculator.calculate(data)
        p1_c = next(c for c in result["energy_intensity"] if c["id"] == "P1")
        assert p1_c["percentage_value"] == "100.0%"

    def test_rule2_co_products_receive_full_emergy(self, calculator):
        """Rule 2: each co-product receives the TOTAL emergy (no split)."""
        src  = _source(uev=1.0, amount=1000.0, node_id="SRC")
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
        src  = _source(uev=1.0, amount=1000.0, node_id="SRC")
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
        src   = _source(uev=1.0, amount=1000.0, node_id="SRC")
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