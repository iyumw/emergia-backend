"""
Domain entities for the emergy calculation engine.
IDs are auto-generated when not provided by the caller.
"""

import uuid
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal


def _generate_id() -> str:
    """Generates a short unique ID based on UUID4."""
    return str(uuid.uuid4())[:8]


class Node(BaseModel):
    id: str = Field(default_factory=_generate_id)
    label: str
    type: Literal["source", "process"]
    # Required only when type="source"
    uev: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    is_multi_output: bool = False
    
    @model_validator(mode="after")
    def validate_source_fields(self) -> "Node":
        if self.type == "source":
            faltantes = []
            if self.uev is None: faltantes.append("UEV (Transformidade)")
            if self.category is None: faltantes.append("Categoria")
            if self.amount is None: faltantes.append("Quantidade (Amount)")
            
            if faltantes:
                raise ValueError(
                    f"A fonte '{self.label}' precisa dos seguintes campos: {', '.join(faltantes)}."
                )
        return self


class Edge(BaseModel):
    id: str = Field(default_factory=_generate_id)
    source: str
    target: str
    amount: float = Field(..., gt=0)
    unit: str = "unit"
    type: str = "energy"


class GraphData(BaseModel):
    nodes: List[Node]
    edges: List[Edge]