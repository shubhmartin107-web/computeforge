from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ParameterDef(BaseModel):
    """Definition of a capability parameter."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum_values: list[str] | None = None


class Capability(BaseModel):
    """Declaration of a capability that the system can perform."""
    name: str
    description: str
    action_type: str = ""
    risk_level: RiskLevel = RiskLevel.MEDIUM
    required_permissions: list[str] = Field(default_factory=list)
    parameters: list[ParameterDef] = Field(default_factory=list)
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
