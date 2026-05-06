import networkx as nx
from app.domain.entities import GraphData
from app.domain.algebra import EmergyAlgebra


class EmergyCalculator:

    def _build_graph(self, data: GraphData) -> tuple[nx.DiGraph, dict]:
        """
        Builds a NetworkX directed graph from the received data.
        Returns the graph and a dict of source emergy values.
        """
        graph = nx.DiGraph()

        # Add source nodes (primary emergy sources)
        source_emergy: dict[str, float] = {}
        for source in data.sources:
            graph.add_node(source.id, name=source.name, is_source=True, is_multi_output=False)
            source_emergy[source.id] = source.get_input_emergy()

        # Add process nodes
        for node in data.nodes:
            graph.add_node(node.id, name=node.name, is_multi_output=node.is_multi_output)

        # Add edges (flows)
        for edge in data.edges:
            graph.add_edge(edge.source_id, edge.target_id, amount=edge.amount)

        return graph, source_emergy

    def _validate(self, graph: nx.DiGraph) -> list[str]:
        """Validates the graph before calculation."""
        errors = []
        if graph.number_of_nodes() == 0:
            errors.append("Graph has no nodes.")
        if graph.number_of_edges() > 3000:
            errors.append(f"Graph exceeds 3,000 edge limit ({graph.number_of_edges()} found).")
        node_ids = set(graph.nodes)
        for u, v in graph.edges:
            if u not in node_ids:
                errors.append(f"Edge source '{u}' not found in nodes.")
            if v not in node_ids:
                errors.append(f"Edge target '{v}' not found in nodes.")
        return errors

    def calculate(self, data: GraphData) -> dict:
        """Main method called by the controller."""
        graph, source_emergy = self._build_graph(data)

        errors = self._validate(graph)
        if errors:
            raise ValueError(f"Invalid graph: {'; '.join(errors)}")

        algebra = EmergyAlgebra(graph, source_emergy)

        # Calculate emergy for every process node
        emergy_by_node: dict[str, float] = {}
        for node_id in graph.nodes:
            if node_id not in source_emergy:  # skip pure source nodes
                emergy_by_node[node_id] = algebra.calculate(node_id)

        # Total emergy = sum of leaf nodes (no outgoing edges)
        leaf_nodes = [n for n in emergy_by_node if graph.out_degree(n) == 0]
        if not leaf_nodes:
            # Graph with pure loops: use the node with the highest emergy
            total_emergy = max(emergy_by_node.values(), default=0.0)
        else:
            total_emergy = sum(emergy_by_node[n] for n in leaf_nodes)

        # Build contribution list
        contributions = [
            {
                "process_id": node_id,
                "process_name": graph.nodes[node_id].get("name", node_id),
                "emergy": emergy_by_node[node_id],
                "percentage": round(
                    (emergy_by_node[node_id] / total_emergy * 100) if total_emergy > 0 else 0.0,
                    2,
                ),
            }
            for node_id in emergy_by_node
        ]

        # Build graph data for front-end visualization
        graph_data = nx.node_link_data(graph)

        return {
            "total_emergy": total_emergy,
            "unit": "sej",
            "scientific_notation": f"{total_emergy:.4e} sej",
            "decimal": f"{total_emergy:.6f} sej",
            "contributions": contributions,
            "has_cycle": not nx.is_directed_acyclic_graph(graph),
            "graph": graph_data,
        }