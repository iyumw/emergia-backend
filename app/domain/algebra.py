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
        graph   — NetworkX directed graph where nodes have 'is_multi_output' attr
                  and edges have 'amount' attr.
        sources — dict mapping source_id -> get_input_emergy() value (float).
        """
        self.graph = graph
        self.sources = sources          # {source_id: emergy_value}
        self._cache: Dict[str, float] = {}
        self._processing: Set[str] = set()

    # ------------------------------------------------------------------
    # Rule 1: source emergy → output
    # ------------------------------------------------------------------
    def _source_emergy(self, node_id: str) -> float:
        """Returns total emergy coming into a root node from primary sources."""
        total = 0.0
        for pred_id in self.graph.predecessors(node_id):
            if pred_id in self.sources:
                total += self.sources[pred_id]
        # Also check if the node itself is a direct source
        if total == 0.0 and node_id in self.sources:
            total = self.sources[node_id]
        return total

    # ------------------------------------------------------------------
    # Rule 2: multi-output → full emergy to each co-product
    # ------------------------------------------------------------------
    def _apply_co_product(self, parent_emergy: float) -> float:
        return parent_emergy  # no split, full value passes through

    # ------------------------------------------------------------------
    # Rule 3: path split → proportional to flow amount
    # ------------------------------------------------------------------
    def _apply_split(self, parent_emergy: float, current_edge_amount: float, parent_id: str) -> float:
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
        """
        Recursively calculates the emergy of a node applying all 4 rules.
        Memoization avoids recomputation; loop detection prevents infinite recursion.
        """
        if node_id in self._cache:
            return self._cache[node_id]

        # Loop detected — return 0 to break recursion (rule 4 handles the rest)
        if node_id in self._processing:
            return 0.0

        self._processing.add(node_id)

        parents = list(self.graph.predecessors(node_id))
        # Filter out pure source nodes (they are not graph process nodes)
        process_parents = [p for p in parents if p not in self.sources]

        if not process_parents:
            # Root node: emergy comes only from primary sources
            emergy = self._source_emergy(node_id)
        else:
            contributions = []

            for parent_id in process_parents:
                parent_emergy = self.calculate(parent_id)
                is_multi_output = self.graph.nodes[parent_id].get("is_multi_output", False)
                parent_outputs = list(self.graph.successors(parent_id))

                if is_multi_output:
                    # Rule 2: co-product receives full emergy
                    contributions.append(self._apply_co_product(parent_emergy))
                elif len(parent_outputs) > 1:
                    # Rule 3: proportional split
                    edge_amount = self.graph[parent_id][node_id]["amount"]
                    contributions.append(self._apply_split(parent_emergy, edge_amount, parent_id))
                else:
                    contributions.append(parent_emergy)

            emergy = self._combine(node_id, contributions, process_parents)

        self._processing.discard(node_id)
        self._cache[node_id] = emergy
        return emergy

    def _get_multi_output_ancestors(self, node_id: str, visited: set = None) -> set:
        """Returns IDs of multi-output ancestor nodes (used to detect co-product convergence)."""
        if visited is None:
            visited = set()
        if node_id in visited:
            return set()
        visited.add(node_id)
        result = set()
        for parent_id in self.graph.predecessors(node_id):
            if parent_id in self.sources:
                continue
            if self.graph.nodes[parent_id].get("is_multi_output", False):
                result.add(parent_id)
            result |= self._get_multi_output_ancestors(parent_id, visited)
        return result

    def _combine(self, node_id: str, contributions: list, parents: list) -> float:
        """
        Rule 4: if co-products from the same multi-output process converge here,
        use only the largest value. Otherwise sum independent contributions.
        """
        if len(parents) < 2:
            return sum(contributions)

        ancestor_groups = [self._get_multi_output_ancestors(p) for p in parents]

        # Check if any two parents share a common multi-output ancestor
        has_convergence = any(
            ancestor_groups[i] & ancestor_groups[j]
            for i in range(len(ancestor_groups))
            for j in range(i + 1, len(ancestor_groups))
        )

        if has_convergence:
            return self._avoid_double_counting(contributions)

        return sum(contributions)