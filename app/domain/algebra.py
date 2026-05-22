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
        self._ancestors_cache: Dict[str, Set[str]] = {}
        self._total_out_amount_cache: Dict[str, float] = {}

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
        # Busca o total acumulado do cache para evitar o loop O(N) repetitivo
        if parent_id in self._total_out_amount_cache:
            total = self._total_out_amount_cache[parent_id]
        else:
            total = sum(
                self.graph[parent_id][child]["amount"]
                for child in self.graph.successors(parent_id)
            )
            self._total_out_amount_cache[parent_id] = total

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
                
                parent_node = self.graph.nodes[parent_id]
                is_multi_output = parent_node.get("is_multi_output", False)
                
                if is_multi_output:
                    contributions.append(self._apply_co_product(parent_emergy))
                else:
                    parent_out_degree = self.graph.out_degree(parent_id)
                    
                    if parent_out_degree > 1:
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
    
    def _get_node_ancestors(self, nid: str, visited: Set[str] = None) -> Set[str]:
        """Busca recursiva de ancestrais com cache global do ciclo de vida da instância."""
        if nid in self._ancestors_cache:
            return self._ancestors_cache[nid]
            
        if visited is None:
            visited = set()
        if nid in visited:
            return set()
            
        visited.add(nid)
        
        anc = set(self.graph.predecessors(nid))
        
        for p in list(anc):
            anc |= self._get_node_ancestors(p, visited)
            
        visited.remove(nid)
        
        self._ancestors_cache[nid] = anc
        return anc

    def _combine(self, node_id: str, contributions: list, parents: list) -> float:
        """Rule 4: avoids double counting when flows share a common origin."""
        if not contributions:
            return 0.0
        if len(parents) < 2:
            return sum(contributions)

        lineages = [self._get_node_ancestors(p) for p in parents]

        has_common_origin = False
        seen_ancestors = set()
        seen_parents = set()

        for i, current_lineage in enumerate(lineages):
            p_current = parents[i]
            
            if (p_current in seen_ancestors or 
                any(p in current_lineage for p in seen_parents) or 
                not current_lineage.isdisjoint(seen_ancestors)):
                has_common_origin = True
                break
                
            seen_ancestors.update(current_lineage)
            seen_parents.add(p_current)

        if has_common_origin:
            return self._avoid_double_counting(contributions)

        return sum(contributions)