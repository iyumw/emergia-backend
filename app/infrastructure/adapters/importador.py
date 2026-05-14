"""
CSV importer for life-cycle inventory data.

Single-file format
──────────────────
The importer now accepts ONE .csv file that contains three clearly delimited
sections, identified by section headers on their own line:

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

Rules
• id is optional in every section — auto-generated when blank or absent.
• Blank lines and lines starting with # are ignored.
• Section order does not matter.
• File size is limited to MAX_FILE_SIZE_BYTES (default 5 MB).

Mandatory columns per section
• [nodes]   → label
• [sources] → label, uev, category
• [edges]   → source, target, amount
"""

import csv
import io
import uuid
import json
import pandas as pd
from io import BytesIO
from typing import NamedTuple, Dict

from app.domain.entities import Node, Edge, GraphData

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

_SECTION_NODES   = "[nodes]"
_SECTION_SOURCES = "[sources]"
_SECTION_EDGES   = "[edges]"
_KNOWN_SECTIONS  = {_SECTION_NODES, _SECTION_SOURCES, _SECTION_EDGES}


# ── Result type ───────────────────────────────────────────────────────────────

class ImportResult(NamedTuple):
    graph_data: GraphData
    nodes: list[Node]
    edges: list[Edge]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _generate_id() -> str:
    return str(uuid.uuid4())[:8]


def _validate_headers(headers: list[str], required: list[str], section: str) -> None:
    missing = [h for h in required if h not in headers]
    if missing:
        raise ValueError(
            f"Na seção '{section}' está faltando as colunas obrigatórias: {missing}. "
            f"As colunas encontradas foram: {headers}"
        )


def _split_sections(content: str) -> dict[str, str]:
    """
    Splits the flat CSV content into per-section raw strings.
    Returns a dict: section_name → csv_block (header + rows).
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        lower = line.lower()
        if lower in _KNOWN_SECTIONS:
            current = lower
            sections[current] = []
            continue

        if current is not None:
            sections[current].append(raw_line)

    if not sections:
        raise ValueError(
            f"Nenhuma seção válida encontrada. O arquivo deve conter pelo menos uma das seguintes seções: "
            f"{sorted(_KNOWN_SECTIONS)}"
        )

    return {k: "\n".join(lines) for k, lines in sections.items()}


# ── Section parsers ───────────────────────────────────────────────────────────

def _parse_nodes_section(content: str) -> list[Node]:
    """
    Columns required : label
    Columns optional : id, is_multi_output
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(reader.fieldnames or [], ["label"], _SECTION_NODES)
    nodes: list[Node] = []
    for row in reader:
        if not row.get("label", "").strip():
            continue
        node_id  = row.get("id", "").strip() or _generate_id()
        is_multi = row.get("is_multi_output", "false").strip().lower() == "true"
        nodes.append(
            Node(
                id=node_id,
                label=row["label"].strip(),
                type="process",
                is_multi_output=is_multi,
            )
        )
    return nodes


def _parse_sources_section(content: str) -> list[Node]:
    """
    Columns required : label, uev, category
    Columns optional : id, amount  (defaults to 1.0)
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["label", "uev", "category"],
        _SECTION_SOURCES,
    )
    nodes: list[Node] = []
    for row in reader:
        if not row.get("label", "").strip():
            continue
        try:
            uev    = float(row["uev"].strip())
            amount = float(row.get("amount", "1").strip() or "1")
        except ValueError as exc:
            raise ValueError(
                f"Valor numérico inválido na seção '{_SECTION_SOURCES}' na linha {dict(row)}: {exc}"
            ) from exc

        node_id = row.get("id", "").strip() or _generate_id()
        nodes.append(
            Node(
                id=node_id,
                label=row["label"].strip(),
                type="source",
                uev=uev,
                category=row["category"].strip(),
                amount=amount,
            )
        )
    return nodes


def _parse_edges_section(content: str) -> list[Edge]:
    """
    Columns required : source, target, amount
    Columns optional : id, unit, type
    """
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["source", "target", "amount"],
        _SECTION_EDGES,
    )
    edges: list[Edge] = []
    for row in reader:
        if not row.get("source", "").strip():
            continue
        try:
            amount = float(row["amount"].strip())
        except ValueError as exc:
            raise ValueError(
                f"Valor numérico inválido na seção '{_SECTION_EDGES}' na linha {dict(row)}: {exc}"
            ) from exc

        edge_id = row.get("id", "").strip() or _generate_id()
        edges.append(
            Edge(
                id=edge_id,
                source=row["source"].strip(),
                target=row["target"].strip(),
                amount=amount,
                unit=row.get("unit", "unit").strip() or "unit",
                type=row.get("type", "energy").strip() or "energy",
            )
        )
    return edges


# ── Public API ────────────────────────────────────────────────────────────────

def build_graph_data_from_single_csv(raw_bytes: bytes) -> ImportResult:
    """
    Parses a single multi-section CSV file and returns an ImportResult
    containing the GraphData, the flat node list and the flat edge list.

    Raises
    ------
    ValueError
        • File exceeds MAX_FILE_SIZE_BYTES.
        • Required section or column is missing.
        • A numeric field contains a non-numeric value.
    UnicodeDecodeError
        • File is not valid UTF-8.
    """
    # ── Size guard ────────────────────────────────────────────────────────────
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise ValueError(
            f"File exceeds the maximum allowed size of {mb} MB "
            f"({len(raw_bytes):,} bytes received)."
        )

    content = raw_bytes.decode("utf-8")
    sections = _split_sections(content)

    # ── Parse each section ────────────────────────────────────────────────────
    process_nodes = (
        _parse_nodes_section(sections[_SECTION_NODES])
        if _SECTION_NODES in sections
        else []
    )
    source_nodes = (
        _parse_sources_section(sections[_SECTION_SOURCES])
        if _SECTION_SOURCES in sections
        else []
    )
    all_nodes: list[Node] = process_nodes + source_nodes

    if not all_nodes:
        raise ValueError(
            "O arquivo deve conter pelo menos um nó (process ou source) para formar um grafo válido."
        )

    edges = (
        _parse_edges_section(sections[_SECTION_EDGES])
        if _SECTION_EDGES in sections
        else []
    )

    graph_data = GraphData(nodes=all_nodes, edges=edges)
    return ImportResult(graph_data=graph_data, nodes=all_nodes, edges=edges)


# ── Backwards-compatible multi-file helper (kept for tests) ──────────────────

def build_graph_data_from_csvs(
    nodes_csv: str,
    sources_csv: str,
    edges_csv: str,
) -> GraphData:
    """
    Kept for backwards compatibility with existing tests.
    Combines three separate CSV strings into a single GraphData object.
    """
    all_nodes = _parse_nodes_section(nodes_csv) + _parse_sources_section(sources_csv)
    edges     = _parse_edges_section(edges_csv)
    return GraphData(nodes=all_nodes, edges=edges)

def _combine_into_result(nodes_csv: str, sources_csv: str, edges_csv: str) -> ImportResult:
    """Reaproveita os validadores existentes do CSV para strings independentes."""
    process_nodes = _parse_nodes_section(nodes_csv) if nodes_csv.strip() else []
    source_nodes = _parse_sources_section(sources_csv) if sources_csv.strip() else []
    all_nodes = process_nodes + source_nodes
    edges = _parse_edges_section(edges_csv) if edges_csv.strip() else []

    if not all_nodes:
        raise ValueError("O grafo precisa de pelo menos um nó (process ou source) para formar um grafo válido.")

    graph_data = GraphData(nodes=all_nodes, edges=edges)
    return ImportResult(graph_data=graph_data, nodes=all_nodes, edges=edges)

def build_from_json(raw_bytes: bytes) -> ImportResult:
    """Lê diretamente do formato JSON."""
    data = json.loads(raw_bytes.decode("utf-8"))
    graph_data = GraphData(**data) # Validação automática via Pydantic
    return ImportResult(graph_data=graph_data, nodes=graph_data.nodes, edges=graph_data.edges)

def build_from_xlsx(raw_bytes: bytes) -> ImportResult:
    """
    Lê arquivos Excel. A ordem das abas não importa, pois a busca é feita pelo nome.
    """
    try:
        xls = pd.ExcelFile(BytesIO(raw_bytes))
        
        nodes_csv = pd.read_excel(xls, 'nodes').to_csv(index=False) if 'nodes' in xls.sheet_names else ""
        sources_csv = pd.read_excel(xls, 'sources').to_csv(index=False) if 'sources' in xls.sheet_names else ""
        edges_csv = pd.read_excel(xls, 'edges').to_csv(index=False) if 'edges' in xls.sheet_names else ""
        
    except Exception as e:
        raise ValueError(
            f"Erro ao ler o arquivo Excel. Verifique se as abas se chamam 'nodes', 'sources' e 'edges'. "
            f"Erro: {e}"
        )
    
    return _combine_into_result(nodes_csv, sources_csv, edges_csv)

def build_graph_data_from_uploads(files_data: Dict[str, bytes]) -> ImportResult:
    """
    Roteador principal: 
    - Se enviar > 1 arquivo: Devem ser os 3 CSVs (nodes, sources, edges).
    - Se enviar 1 arquivo: Deve ser .json ou .xlsx.
    """
    
    # Cenário 1: Múltiplos arquivos (3 CSVs separados)
    if len(files_data) > 1:
        nodes_csv, sources_csv, edges_csv = "", "", ""
        for name, content in files_data.items():
            txt = content.decode("utf-8")
            if "node" in name: nodes_csv = txt
            elif "source" in name: sources_csv = txt
            elif "edge" in name: edges_csv = txt
            
        if not nodes_csv or not edges_csv:
            raise ValueError("Para múltiplos arquivos, envie ao menos 'nodes' e 'edges' em CSVs separados.")
            
        return _combine_into_result(nodes_csv, sources_csv, edges_csv)

    # Cenário 2: Arquivo único (Apenas JSON ou XLSX)
    if len(files_data) == 1:
        name, content = list(files_data.items())[0]
        name = name.lower()
        
        if name.endswith(".json"):
            return build_from_json(content)
        elif name.endswith(".xlsx"):
            return build_from_xlsx(content)
        elif name.endswith(".csv"):
            raise ValueError("O sistema não aceita um único arquivo .csv. Envie os 3 CSVs separados ou use .xlsx/.json.")

    raise ValueError("Formato não suportado. Envie .json, .xlsx ou os 3 .csv separados.")