import networkx as nx
import time
import uuid
from app.domain.entities import GraphData
from app.domain.algebra import EmergyAlgebra


class EmergyCalculator:

    def _build_graph(self, data: GraphData) -> tuple[nx.DiGraph, dict]:
        graph = nx.DiGraph()
        source_emergy: dict[str, float] = {}

        allowed_ids = {node.id for node in data.Nos}

        for node in data.Nos:
            graph.add_node(
                node.id,
                label=node.label,
                tipo=node.tipo,
                is_multi_output=node.is_multi_output,
            )
            if node.tipo == "source":
                source_emergy[node.id] = (node.uev or 0) * (node.quantidade or 0)

        for edge in data.Arestas:
            if edge.origem not in allowed_ids:
                raise ValueError(
                    f"Aresta: nó de origem '{edge.origem}' não encontrado na lista de nós."
                )
            if edge.destino not in allowed_ids:
                raise ValueError(
                    f"Aresta: nó de destino '{edge.destino}' não encontrado na lista de nós."
                )
            eid = edge.id if getattr(edge, "id", None) else str(uuid.uuid4())[:8]
            graph.add_edge(edge.origem, edge.destino, quantidade=edge.quantidade, id=eid)

        return graph, source_emergy

    def _validate(self, graph: nx.DiGraph) -> list[str]:
        """Valida a integridade do grafo antes do cálculo."""
        errors = []
        if graph.number_of_nodes() == 0:
            errors.append("Grafo vazio: não há nós.")

        node_ids = set(graph.nodes)
        for u, v in graph.edges:
            if u not in node_ids:
                errors.append(f"Aresta: origem '{u}' não pertence ao conjunto de nós.")
            if v not in node_ids:
                errors.append(f"Aresta: destino '{v}' não pertence ao conjunto de nós.")
        return errors

    def calculate(self, data: GraphData) -> dict:
        """Executa o cálculo de emergia aplicando as 4 regras de Odum."""
        start_time = time.perf_counter()

        graph, source_emergy = self._build_graph(data)

        errors = self._validate(graph)
        if errors:
            raise ValueError(f"Grafo inválido: {'; '.join(errors)}")

        algebra = EmergyAlgebra(graph, source_emergy)

        emergy_by_node: dict[str, float] = {}
        for node_id in graph.nodes:
            node_data = graph.nodes[node_id]
            if node_data.get("tipo") == "process":
                emergy_by_node[node_id] = algebra.calculate(node_id)

        leaf_nodes = [n for n in emergy_by_node if graph.out_degree(n) == 0]
        total_emergy = (
            sum(emergy_by_node[n] for n in leaf_nodes) if leaf_nodes else 0.0
        )

        end_time = time.perf_counter()

        return {
            "total_emergy": total_emergy,
            "unit": "sej",
            "stats": {
                "nodes_count": graph.number_of_nodes(),
                "edges_count": graph.number_of_edges(),
                "processing_time_ms": round((end_time - start_time) * 1000, 2),
            },
            "contributions": [
                {
                    "id": nid,
                    "label": graph.nodes[nid].get("label", nid),
                    "value": val,
                    "percent": (
                        round((val / total_emergy) * 100, 2) if total_emergy > 0 else 0
                    ),
                }
                for nid, val in emergy_by_node.items()
            ],
            "graph": nx.node_link_data(graph),
        }