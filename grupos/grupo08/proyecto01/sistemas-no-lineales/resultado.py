from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class EstadoMetodo(str, Enum):
    CONVERGED = "converged"
    MAX_ITER = "max_iter"
    DIVERGED = "diverged"
    SINGULAR_JACOBIAN = "singular_jacobian"
    INVALID_INPUT = "invalid_input"


class ResultadoMetodo(BaseModel):
    method: str
    status: EstadoMetodo
    solution: Optional[List[float]] = None
    iterations: int = 0
    final_error: Optional[float] = None
    final_residual: Optional[float] = None
    trajectory: List[List[float]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    message: Optional[str] = None