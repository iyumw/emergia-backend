import networkx as nx
import time
import uuid
from app.domain.entities import GraphData
from app.domain.algebra import EmergyAlgebra
from app.domain.exceptions import InvalidGraphError, NodeNotFoundError


class EmergyCalculator:

    def _build_graph(self, data: GraphData) -> tuple[nx.DiGraph, dict]:
        graph = nx.DiGraph()
        source_emergy: dict[str, float] = {}

        allowed_ids = {node.id for node in data.nodes}

        for node in data.nodes:
            graph.add_node(
                node.id,
                label=node.label,
                type=node.type,
                is_multi_output=node.is_multi_output,
            )
            if node.type == "source":
                source_emergy[node.id] = (node.uev or 0.0) * (node.amount or 0.0)

        for edge in data.edges:
            if edge.source not in allowed_ids:
                raise NodeNotFoundError(
                    f"A conexão tenta sair de '{edge.source}', mas esse item não existe na lista de nós."
                )
            if edge.target not in allowed_ids:
                raise NodeNotFoundError(
                    f"A conexão tenta entrar em '{edge.target}', mas esse item não existe na lista de nós."
                )
            eid = edge.id if getattr(edge, "id", None) else str(uuid.uuid4())[:8]
            graph.add_edge(
                edge.source,
                edge.target,
                amount=edge.amount,
                id=eid,
            )

        return graph, source_emergy

    def _validate(self, graph: nx.DiGraph) -> list[str]:
        errors = []
        if graph.number_of_nodes() == 0:
            errors.append("Grafo vazio: nenhum item (nó) foi fornecido.")
        node_ids = set(graph.nodes)
        for u, v in graph.edges:
            if u not in node_ids:
                errors.append(f"A conexão tenta sair de '{u}', mas esse item não existe na lista de nós.")
            if v not in node_ids:
                errors.append(f"A conexão tenta entrar em '{v}', mas esse item não existe na lista de nós.")
        return errors

    def calculate(self, data: GraphData) -> dict:
        """Runs the emergy calculation applying Odum's 4 rules."""
        start_time = time.perf_counter()

        graph, source_emergy = self._build_graph(data)

        errors = self._validate(graph)
        if errors:
            raise InvalidGraphError(f"Grafo inválido. Problemas encontrados no diagrama: {'; '.join(errors)}")

        algebra = EmergyAlgebra(graph, source_emergy)

        emergy_by_node: dict[str, float] = {}
        for node_id in graph.nodes:
            if graph.nodes[node_id].get("type") == "process":
                emergy_by_node[node_id] = algebra.calculate(node_id)

        leaf_nodes = [n for n in emergy_by_node if graph.out_degree(n) == 0]
        total_emergy = (
            sum(emergy_by_node[n] for n in leaf_nodes) if leaf_nodes else 0.0
        )

        energy_intensity = []
        for nid, valor in emergy_by_node.items():
            percent = (valor / total_emergy * 100) if total_emergy > 0 else 0
            energy_intensity.append({
                "id": nid,
                "label": graph.nodes[nid].get("label", nid),
                "percentage_value": f"{round(percent, 2)}%"
            })
        
        end_time = time.perf_counter()

        return {
            "total_emergy": total_emergy,
            "unit": "sej",
            "energy_intensity": energy_intensity,
            "stats": {
                "paths_analyzed": algebra.paths_count,
                "nodes_count": graph.number_of_nodes(),
                "edges_count": graph.number_of_edges(),
                "processing_time_ms": round((end_time - start_time) * 1000, 2),
            }
        }