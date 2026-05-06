import json
import io
from typing import Annotated

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.domain.entities import GraphData
from app.application.calculador_service import EmergyCalculator
from app.infrastructure.adapters.importador import build_graph_data_from_csvs

router = APIRouter()
calculator = EmergyCalculator()


# ── Calculate from JSON ──────────────────────────────────────────────────────

@router.post("/calculate")
async def calculate_emergy(data: GraphData):
    """
    Receives nodes, edges and sources as JSON and returns the total emergy.
    
    Example payload:
    {
      "nodes": [
        {"id": "P1", "name": "Cultivation", "is_multi_output": false},
        {"id": "P2", "name": "Harvest",     "is_multi_output": false}
      ],
      "edges": [
        {"source_id": "SRC_SUN", "target_id": "P1", "amount": 3.5e14},
        {"source_id": "P1",      "target_id": "P2", "amount": 1000}
      ],
      "sources": [
        {"id": "SRC_SUN", "name": "Solar Energy", "uev": 1.0, "category": "renewable", "amount": 3.5e14}
      ]
    }
    """
    try:
        result = calculator.calculate(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


# ── Import from CSV files ────────────────────────────────────────────────────

@router.post("/import")
async def import_csvs(
    nodes: Annotated[UploadFile, File(description="nodes.csv  →  id, name, is_multi_output")],
    sources: Annotated[UploadFile, File(description="sources.csv  →  id, name, uev, category, amount")],
    edges: Annotated[UploadFile, File(description="edges.csv  →  source_id, target_id, amount")],
):
    """
    Receives three CSV files and returns the total emergy calculation.
    File columns:
      nodes.csv   — id, name, is_multi_output
      sources.csv — id, name, uev, category, amount
      edges.csv   — source_id, target_id, amount
    """
    try:
        nodes_csv = (await nodes.read()).decode("utf-8")
        sources_csv = (await sources.read()).decode("utf-8")
        edges_csv = (await edges.read()).decode("utf-8")

        data = build_graph_data_from_csvs(nodes_csv, sources_csv, edges_csv)
        result = calculator.calculate(data)
        return result
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


# ── Export result as downloadable JSON ───────────────────────────────────────

@router.post("/export")
async def export_result(data: GraphData):
    """Calculates and returns the result as a downloadable JSON file."""
    try:
        result = calculator.calculate(data)
        content = json.dumps(result, ensure_ascii=False, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode("utf-8")),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=emergy_result.json"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))