"""
CSV importer for life cycle inventory data.

Expected CSV formats:

  nodes.csv
  ---------
  id,name,is_multi_output
  P1,Wood Extraction,false
  P2,Transport,false
  P3,Cogeneration,true

  sources.csv
  -----------
  id,name,uev,category,amount
  SRC_SUN,Solar Energy,1.0,renewable,3.5e14
  SRC_RAIN,Rain,1.54e4,renewable,1000

  edges.csv
  ---------
  source_id,target_id,amount
  SRC_SUN,P1,3.5e14
  P1,P2,1000
  P2,P3,500
"""

import csv
import io
from app.domain.entities import EmergySource, Flow, GraphData, Process


def _validate_headers(headers: list, required: list, filename: str) -> None:
    missing = [h for h in required if h not in headers]
    if missing:
        raise ValueError(
            f"File '{filename}' is missing columns: {missing}. "
            f"Found: {headers}"
        )


def parse_nodes(content: str) -> list[Process]:
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(reader.fieldnames or [], ["id", "name"], "nodes.csv")
    nodes = []
    for row in reader:
        if not row.get("id", "").strip():
            continue
        is_multi = row.get("is_multi_output", "false").strip().lower() == "true"
        nodes.append(
            Process(
                id=row["id"].strip(),
                name=row["name"].strip(),
                is_multi_output=is_multi,
            )
        )
    return nodes


def parse_sources(content: str) -> list[EmergySource]:
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["id", "name", "uev", "category"],
        "sources.csv",
    )
    sources = []
    for row in reader:
        if not row.get("id", "").strip():
            continue
        try:
            uev = float(row["uev"].strip())
            amount = float(row.get("amount", "1").strip() or "1")
        except ValueError as e:
            raise ValueError(f"Invalid numeric value in row {dict(row)}: {e}")
        sources.append(
            EmergySource(
                id=row["id"].strip(),
                name=row["name"].strip(),
                uev=uev,
                category=row["category"].strip(),
                amount=amount,
            )
        )
    return sources


def parse_edges(content: str) -> list[Flow]:
    reader = csv.DictReader(io.StringIO(content))
    _validate_headers(
        reader.fieldnames or [],
        ["source_id", "target_id", "amount"],
        "edges.csv",
    )
    edges = []
    for row in reader:
        if not row.get("source_id", "").strip():
            continue
        try:
            amount = float(row["amount"].strip())
        except ValueError as e:
            raise ValueError(f"Invalid amount in row {dict(row)}: {e}")
        edges.append(
            Flow(
                source_id=row["source_id"].strip(),
                target_id=row["target_id"].strip(),
                amount=amount,
            )
        )
    return edges


def build_graph_data_from_csvs(
    nodes_csv: str,
    sources_csv: str,
    edges_csv: str,
) -> GraphData:
    """Combines the three CSVs into a single GraphData object."""
    return GraphData(
        nodes=parse_nodes(nodes_csv),
        sources=parse_sources(sources_csv),
        edges=parse_edges(edges_csv),
    )