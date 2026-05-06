from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class Process(BaseModel):
    id: str
    name: str
    is_multi_output: bool = False


class Flow(BaseModel):
    source_id: str
    target_id: str
    amount: float = Field(..., gt=0)

    @field_validator("target_id")
    @classmethod
    def source_differs_from_target(cls, v: str, info) -> str:
        if "source_id" in info.data and v == info.data["source_id"]:
            raise ValueError("source_id and target_id cannot be the same")
        return v

    def get_ratio(self, sibling_flows: List["Flow"]) -> float:
        total = sum(f.amount for f in sibling_flows)
        if total == 0:
            return 0.0
        return self.amount / total


class EmergySource(BaseModel):
    id: str
    name: str
    uev: float = Field(..., gt=0)       # Unit Emergy Value (sej/unit)
    category: str                        # renewable | non_renewable | material | service
    amount: float = Field(default=1.0, gt=0)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"renewable", "non_renewable", "material", "service"}
        if v not in allowed:
            raise ValueError(f"category must be one of: {allowed}")
        return v

    def get_input_emergy(self) -> float:
        return self.uev * self.amount


class GraphData(BaseModel):
    """Main contract received by the /calculate endpoint."""
    nodes: List[Process]
    edges: List[Flow]
    sources: List[EmergySource]