from app.domain.entities import GraphData
from tests.helpers import _source, _process, _edge

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
