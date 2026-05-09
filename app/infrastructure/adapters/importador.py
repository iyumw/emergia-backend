"""
Importador CSV para dados de inventário do ciclo de vida,
adaptado ao esquema unificado de Nó/Aresta.

IDs dos nós são gerados automaticamente quando a coluna 'id' não estiver
presente no CSV ou quando a célula estiver vazia.
"""

import csv
import io
import uuid
from app.domain.entities import No, Aresta, GraphData


def _validate_headers(headers: list, required: list, filename: str) -> None:
    missing = [h for h in required if h not in headers]
    if missing:
        raise ValueError(
            f"Arquivo '{filename}' está sem as colunas obrigatórias: {missing}. "
            f"Encontradas: {headers}"
        )


def _gerar_id() -> str:
    return str(uuid.uuid4())[:8]


def parse_nodes(content: str) -> list[No]:
    """
    Colunas obrigatórias: label
    Colunas opcionais:    id (gerado automaticamente se ausente), is_multi_output
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(reader.fieldnames or [], ["label"], "nodes.csv")
    nodes = []
    for row in reader:
        if not row.get("label", "").strip():
            continue
        node_id = row.get("id", "").strip() or _gerar_id()
        is_multi = row.get("is_multi_output", "false").strip().lower() == "true"
        nodes.append(
            No(
                id=node_id,
                label=row["label"].strip(),
                tipo="process",
                is_multi_output=is_multi,
            )
        )
    return nodes


def parse_sources(content: str) -> list[No]:
    """
    Colunas obrigatórias: label, uev, categoria
    Colunas opcionais:    id (gerado automaticamente se ausente), quantidade
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["label", "uev", "categoria"],
        "sources.csv",
    )
    nodes = []
    for row in reader:
        if not row.get("label", "").strip():
            continue
        try:
            uev = float(row["uev"].strip())
            quantidade = float(row.get("quantidade", "1").strip() or "1")
        except ValueError as e:
            raise ValueError(f"Valor numérico inválido na linha {dict(row)}: {e}")

        node_id = row.get("id", "").strip() or _gerar_id()
        nodes.append(
            No(
                id=node_id,
                label=row["label"].strip(),
                tipo="source",
                uev=uev,
                categoria=row["categoria"].strip(),
                quantidade=quantidade,
            )
        )
    return nodes


def parse_edges(content: str, node_ids: set[str]) -> list[Aresta]:
    """
    Colunas obrigatórias: origem, destino, quantidade
    Colunas opcionais:    id, unidade, tipo

    'origem' e 'destino' podem referenciar o 'id' do nó (se fornecido no CSV)
    ou o 'label' do nó (busca por label como fallback).
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["origem", "destino", "quantidade"],
        "edges.csv",
    )
    edges = []
    for row in reader:
        if not row.get("origem", "").strip():
            continue
        try:
            quantidade = float(row["quantidade"].strip())
        except ValueError as e:
            raise ValueError(f"Quantidade inválida na linha {dict(row)}: {e}")

        edge_id = row.get("id", "").strip() or _gerar_id()
        edges.append(
            Aresta(
                id=edge_id,
                origem=row["origem"].strip(),
                destino=row["destino"].strip(),
                quantidade=quantidade,
                unidade=row.get("unidade", "unit").strip(),
                tipo=row.get("tipo", "energy").strip(),
            )
        )
    return edges


def build_graph_data_from_csvs(
    nodes_csv: str,
    sources_csv: str,
    edges_csv: str,
) -> GraphData:
    """Combina os três CSVs em um único objeto GraphData."""
    all_nodes = parse_nodes(nodes_csv) + parse_sources(sources_csv)
    node_ids = {n.id for n in all_nodes}
    return GraphData(
        Nos=all_nodes,
        Arestas=parse_edges(edges_csv, node_ids),
    )