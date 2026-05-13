"""
Implementation of H.T. Odum's 4 Emergy Algebra rules:

  Rule 1 — All emergy from a source is assigned to its output.
  Rule 2 — Co-products from a multi-output process each receive the TOTAL emergy (no split).
  Rule 3 — When a path splits, emergy is distributed PROPORTIONALLY to flow amounts.
  Rule 4 — Emergy cannot be counted twice. When co-products rejoin or feedbacks occur,
            only the LARGEST value is used.
"""

import networkx as nx
from typing import Dict, Set


class EmergyAlgebra:

    def __init__(self, graph: nx.DiGraph, sources: dict):
        """
        graph   — NetworkX directed graph where nodes carry 'is_multi_output' and
                  edges carry 'amount'.
        sources — {source_id: emergy_value (float)}
        """
        self.graph = graph
        self.sources = sources
        self._cache: Dict[str, float] = {}
        self._processing: Set[str] = set()
        self.paths_count = 0

    # ------------------------------------------------------------------
    # Rule 1: source emergy → output
    # ------------------------------------------------------------------
    def _source_emergy(self, node_id: str) -> float:
        total = 0.0
        for pred_id in self.graph.predecessors(node_id):
            if pred_id in self.sources:
                total += self.sources[pred_id]
        if total == 0.0 and node_id in self.sources:
            total = self.sources[node_id]
        return total

    # ------------------------------------------------------------------
    # Rule 2: multi-output → full emergy to each co-product
    # ------------------------------------------------------------------
    def _apply_co_product(self, parent_emergy: float) -> float:
        return parent_emergy

    # ------------------------------------------------------------------
    # Rule 3: path split → proportional to flow amount
    # ------------------------------------------------------------------
    def _apply_split(
        self, parent_emergy: float, current_edge_amount: float, parent_id: str
    ) -> float:
        sibling_amounts = [
            self.graph[parent_id][child]["amount"]
            for child in self.graph.successors(parent_id)
        ]
        total = sum(sibling_amounts)
        if total == 0:
            return 0.0
        return parent_emergy * (current_edge_amount / total)

    # ------------------------------------------------------------------
    # Rule 4: avoid double counting → use the largest value
    # ------------------------------------------------------------------
    def _avoid_double_counting(self, values: list) -> float:
        return max(values) if values else 0.0

    # ------------------------------------------------------------------
    # DFS with memoization
    # ------------------------------------------------------------------
    def calculate(self, node_id: str) -> float:
        self.paths_count += 1
        if node_id in self._cache:
            return self._cache[node_id]

        if node_id in self._processing:
            return 0.0  # loop detected — break recursion

        self._processing.add(node_id)

        parents = list(self.graph.predecessors(node_id))
        process_parents = [p for p in parents if p not in self.sources]

        if not process_parents:
            emergy = self._source_emergy(node_id)
        else:
            contributions = []
            for parent_id in process_parents:
                parent_emergy = self.calculate(parent_id)
                is_multi_output = self.graph.nodes[parent_id].get("is_multi_output", False)
                parent_outputs = list(self.graph.successors(parent_id))

                if is_multi_output:
                    contributions.append(self._apply_co_product(parent_emergy))
                elif len(parent_outputs) > 1:
                    edge_amount = self.graph[parent_id][node_id]["amount"]
                    contributions.append(
                        self._apply_split(parent_emergy, edge_amount, parent_id)
                    )
                else:
                    contributions.append(parent_emergy)

            emergy = self._combine(node_id, contributions, process_parents)

        self._processing.discard(node_id)
        self._cache[node_id] = emergy
        return emergy

    def _combine(self, node_id: str, contributions: list, parents: list) -> float:
        """Rule 4: avoids double counting when flows share a common origin."""
        if not contributions:
            return 0.0
        if len(parents) < 2:
            return sum(contributions)

        def get_all_ancestors(nid, visited=None):
            if visited is None:
                visited = set()
            if nid in visited:
                return set()
            visited.add(nid)
            anc = set(self.graph.predecessors(nid))
            for p in list(anc):
                anc |= get_all_ancestors(p, visited)
            return anc

        lineages = [get_all_ancestors(p) for p in parents]

        has_common_origin = False
        for i in range(len(lineages)):
            for j in range(i + 1, len(lineages)):
                if (
                    lineages[i] & lineages[j]
                    or (parents[i] in lineages[j])
                    or (parents[j] in lineages[i])
                ):
                    has_common_origin = True
                    break
            if has_common_origin:
                break

        if has_common_origin:
            return self._avoid_double_counting(contributions)

        return sum(contributions)