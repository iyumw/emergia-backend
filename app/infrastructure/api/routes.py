"""
REST API routes for the emergy calculation engine.
EmergyCalculator is injected via FastAPI Depends (dependency inversion).
"""

import base64
import io
from typing import Annotated, List, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4

from app.domain.entities import GraphData
from app.application.emergy_calculator import EmergyCalculator
from app.infrastructure.adapters.importador import build_graph_data_from_uploads
from app.domain.glossary import get_glossary
from app.domain.graph_store import save_graph, get_graph

router = APIRouter()


# ── Dependency injection ──────────────────────────────────────────────────────

def get_calculator() -> EmergyCalculator:
    """Factory for EmergyCalculator injection via Depends."""
    return EmergyCalculator()


# ── Calculate from JSON ───────────────────────────────────────────────────────


@router.post("/calculate")
async def calculate_emergy(
    data: GraphData,
    calculator: Annotated[EmergyCalculator, Depends(get_calculator)],
):
    """
    Receives nodes and edges as JSON and returns the total emergy.

    Node `id` is **optional** — auto-generated when omitted.

    Example payload:

        {
          "nodes": [
            {
              "id": "SUN_01",
              "label": "Solar Energy",
              "type": "source",
              "uev": 1.0,
              "category": "renewable",
              "amount": 3500000.0
            },
            { "id": "P1", "label": "Plantation", "type": "process" },
            { "id": "P2", "label": "Harvest",    "type": "process" }
          ],
          "edges": [
            { "source": "SUN_01", "target": "P1", "amount": 3500000.0, "unit": "sej" },
            { "source": "P1",     "target": "P2", "amount": 1000.0,    "unit": "kg"  }
          ]
        }
    """
    try:
        result = calculator.calculate(data)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Calculation error: {exc}")


# ── Import from uploaded files ─────────────────────────────────────────────


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_data(
    files: List[UploadFile] = File(
        description="Envie 1 arquivo (.json, .xlsx) ou os 3 CSVs separados (nodes, sources, edges)."
    ),
    calculator: Annotated[EmergyCalculator, Depends(get_calculator)] = None,
):
    if not files:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    ALLOWED_EXTENSIONS = {'.csv', '.json', '.xlsx'}
    files_data = {}

    for file in files:
        filename = file.filename.lower()
        # Validação de Extensão
        if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            raise HTTPException(
                status_code=400, 
                detail=f"Arquivo {file.filename} não suportado. Use apenas .csv, .json ou .xlsx."
            )
        
        files_data[filename] = await file.read()

    try:
        import_result = build_graph_data_from_uploads(files_data)
        calc_result = calculator.calculate(import_result.graph_data)
    except (ValueError, UnicodeDecodeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro durante a importação: {exc}")

    # Salva a sessão no formato padronizado
    nodes_payload = [node.model_dump() for node in import_result.nodes]
    edges_payload = [edge.model_dump() for edge in import_result.edges]

    graph_id = save_graph(
        nodes=nodes_payload,
        edges=edges_payload,
        result=calc_result,
    )

    return {
        "graph_id": graph_id,
        "expires_in_seconds": 3600,
    }


# ── Retrieve stored graph by graph ID ───────────────────────────────────────


@router.get("/graph/{graph_id}")
async def get_graph_by_id(graph_id: str):
    """
    Retorna o grafo completo e os resultados dos cálculos para um ID específico.
    Grafos expiram após 1 hora (configurável) e são removidos automaticamente do armazenamento em memória.

    ## Estrutura do Retorno:

    * **graph_id**: Identificador único da análise.
    * **created_at**: Timestamp de criação
    * **nodes**: Lista completa dos nós com todos os metadados (UEV, Categoria, etc.). **Use esta lista para tabelas ou formulários de edição.**
    * **edges**: Lista de todas as arestas.
    * **result**: Objeto contendo o processamento final:
        * **total_emergy**: Valor numérico final da emergia do sistema.
        * **unit**: Unidade de medida (padrão: sej).
        * **stats**: Quantidade de nós/arestas e tempo de processamento em ms.
    """
    graph = get_graph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Grafo não encontrado.")
    return graph


# ── Export result as downloadable JSON ────────────────────────────────────────


@router.post("/export/pdf")
async def export_pdf(graph_id: str, config: dict[str, Any] = {}):
    """
    Gera um PDF customizável incluindo a captura visual do grafo.

    ## Parâmetros:
    - **graph_id**: ID do grafo para referência no relatório.
    - **config**: JSON com dados de customização.

    ## Exemplo de Request Body (config):
    ```json
    {
      "title": "Análise de Sistema de Silagem",
      "graph_image": "data:image/png;base64,iVBORw0KGgoAAAANSUh...",
      "show_stats": true
    }
    ```

    ## Notas para o Front-end (Cytoscape):
    1. Gere a imagem com `cy.png({ output: 'base64' })`.
    2. Envie a string resultante no campo `graph_image`.
    3. Trate a resposta desta rota como um **Blob** para disparar o download.
    """
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    # Título e Identificação
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, altura - 50, config.get("title", "Relatório de Emergia"))
    
    p.setFont("Helvetica", 10)
    p.drawString(50, altura - 70, f"ID do Grafo: {graph_id}")
    p.drawString(50, altura - 85, "Status: Calculado com sucesso")

    # Processamento da Imagem Base64
    graph_image_base64 = config.get("graph_image")
    
    if graph_image_base64:
        try:
            # Limpa o prefixo do data URI se existir
            if "," in graph_image_base64:
                encoded = graph_image_base64.split(",", 1)[1]
            else:
                encoded = graph_image_base64
            
            # Converte de string Base64 para Bytes
            image_data = base64.b64decode(encoded)
            img_buffer = io.BytesIO(image_data)
            img_reader = ImageReader(img_buffer)
            
            # Desenha a imagem no PDF (x, y, largura, altura)
            # preserveAspectRatio garante que o grafo não fique esticado
            p.drawImage(img_reader, 50, altura - 450, width=500, height=350, 
                        preserveAspectRatio=True, mask='auto')
            
        except Exception as e:
            p.setFont("Helvetica-Oblique", 8)
            p.setFillColorRGB(0.7, 0, 0)
            p.drawString(50, altura - 100, f"Erro ao processar imagem: {str(e)}")
            p.setFillColorRGB(0, 0, 0)

    p.showPage()
    p.save()

    buffer.seek(0)
    return StreamingResponse(
        buffer, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{graph_id}.pdf",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


# ── Glossary ──────────────────────────────────────────────────────────────────


@router.get("/glossary")
async def glossary():
    """
    Returns the emergy concepts glossary and the methodology reference.
    Fulfils optional requirement RFO 2.
    """
    return get_glossary()