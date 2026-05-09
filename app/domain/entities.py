"""
Entidades de domínio do motor de cálculo emergético.
IDs são gerados automaticamente quando não fornecidos pelo usuário.
"""

import uuid
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal


def _gerar_id() -> str:
    """Gera um ID único curto baseado em UUID."""
    return str(uuid.uuid4())[:8]


class No(BaseModel):
    id: str = Field(default_factory=_gerar_id)
    label: str
    tipo: Literal["source", "process"]
    # Campos obrigatórios apenas para tipo="source"
    uev: Optional[float] = Field(None, gt=0)
    categoria: Optional[str] = None
    quantidade: Optional[float] = Field(None, gt=0)
    is_multi_output: bool = False

    @model_validator(mode='after')
    def validate_source_fields(self) -> 'No':
        if self.tipo == "source":
            if self.uev is None or self.categoria is None or self.quantidade is None:
                raise ValueError(
                    f"Nó '{self.label}' do tipo 'source' exige 'uev', 'categoria' e 'quantidade'."
                )
        return self


class Aresta(BaseModel):
    id: str = Field(default_factory=_gerar_id)
    origem: str
    destino: str
    quantidade: float = Field(..., gt=0)
    unidade: str = "unit"
    tipo: str = "energy"


class GraphData(BaseModel):
    Nos: List[No]
    Arestas: List[Aresta]