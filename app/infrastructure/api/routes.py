"""
Rotas da API REST do motor de cálculo emergético.
EmergyCalculator é injetado via FastAPI Depends (inversão de dependência).
"""

import json
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.domain.entities import GraphData
from app.application.emergy_calculator import EmergyCalculator
from app.infrastructure.adapters.importador import build_graph_data_from_csvs
from app.domain.glossario import get_glossario

router = APIRouter()


# ── Injeção de dependência ────────────────────────────────────────────────────

def get_calculator() -> EmergyCalculator:
    """Factory para injeção de EmergyCalculator via Depends."""
    return EmergyCalculator()


# ── Calcular a partir de JSON ─────────────────────────────────────────────────


@router.post("/calculate")
async def calculate_emergy(
    data: GraphData,
    calculator: Annotated[EmergyCalculator, Depends(get_calculator)],
):
    """
    Recebe nós e arestas como JSON e retorna a emergia total.

    Os IDs dos nós são **opcionais**: se omitidos, são gerados automaticamente.

    Payload de exemplo (IDs explícitos):

        {
          "Nos": [
            {
              "id": "SOL_01",
              "label": "Energia Solar",
              "tipo": "source",
              "uev": 1.0,
              "categoria": "renovável",
              "quantidade": 3500000.0,
              "is_multi_output": false
            },
            { 
              "id": "P1", 
              "label": "Plantação", 
              "tipo": "process",
              "is_multi_output": false 
            },
            { 
              "id": "P2", 
              "label": "Colheita",  
              "tipo": "process",
              "is_multi_output": false 
            }
          ],
          "Arestas": [
            { 
              "id": "E1",
              "origem": "SOL_01", 
              "destino": "P1", 
              "quantidade": 3500000.0,
              "unidade": "sej" 
            },
            { 
              "id": "E2",
              "origem": "P1",   
              "destino": "P2", 
              "quantidade": 1000.0,
              "unidade": "kg"
            }
          ]
        }
    """
    try:
        result = calculator.calculate(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no cálculo: {str(e)}")


# ── Importar a partir de arquivos CSV ─────────────────────────────────────────


@router.post("/import")
async def import_csvs(
    nodes: Annotated[
        UploadFile, File(description="nodes.csv  →  label (obrig.), id e is_multi_output (opcionais)")
    ],
    sources: Annotated[
        UploadFile, File(description="sources.csv  →  label, uev, categoria (obrig.), id e quantidade (opcionais)")
    ],
    edges: Annotated[
        UploadFile, File(description="edges.csv  →  origem, destino, quantidade (obrig.), id, unidade e tipo (opcionais)")
    ],
    calculator: Annotated[EmergyCalculator, Depends(get_calculator)],
):
    """
    Recebe três arquivos CSV e retorna o resultado do cálculo emergético.

    Colunas:
      nodes.csv   — label (obrig.), id (opcional), is_multi_output (opcional)
      sources.csv — label, uev, categoria (obrig.), id (opcional), quantidade (opcional)
      edges.csv   — origem, destino, quantidade (obrig.), id (opcional), unidade, tipo
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
        raise HTTPException(status_code=500, detail=f"Erro na importação: {str(e)}")


# ── Exportar resultado como JSON para download ────────────────────────────────


@router.post("/export")
async def export_result(
    data: GraphData,
    calculator: Annotated[EmergyCalculator, Depends(get_calculator)],
):
    """Calcula e retorna o resultado como arquivo JSON para download."""
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação: {str(e)}")


# ── Glossário de conceitos emergéticos ───────────────────────────────────────


@router.get("/glossario")
async def glossario():
    """
    Retorna o glossário de conceitos emergéticos e da metodologia utilizada.
    Atende ao RFO 2 do planejamento do sistema.
    """
    return get_glossario()