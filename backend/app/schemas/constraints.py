from pydantic import BaseModel


class MaterialOverride(BaseModel):
    material_name: str
    preferred_grade_or_brand: str


class ConstraintsRequest(BaseModel):
    budget_cap: float | None = None
    material_overrides: list[MaterialOverride] = []


class ConstraintsResponse(BaseModel):
    budget_cap: float | None
    material_overrides: list[MaterialOverride]
    warnings: list[str]
