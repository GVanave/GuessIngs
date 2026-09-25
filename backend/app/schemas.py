"""Request/response models (all API input is validated here)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_strength
from app.services.normalization import MAX_TEXT_LENGTH


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v or None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean(v) or ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme: Literal["system", "light", "dark"] = "system"
    show_nova: bool = True
    save_history: bool = True
    ai_explanations: bool = True


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    preferences: Preferences
    created_at: datetime

    @field_validator("preferences", mode="before")
    @classmethod
    def _prefs(cls, v):
        return Preferences(**(v or {}))


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    preferences: Preferences | None = None


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class AnalyzeIn(BaseModel):
    ingredients_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    product_name: str | None = Field(default=None, max_length=160)
    brand: str | None = Field(default=None, max_length=120)
    sodium_mg_per_100g: float | None = Field(default=None, ge=0, le=40000)
    source: Literal["manual", "upload", "camera"] = "manual"
    ocr_text: str | None = Field(default=None, max_length=20000)

    @field_validator("product_name", "brand")
    @classmethod
    def _names(cls, v):
        return _clean(v)


class ExtractionOut(BaseModel):
    ingredients_text: str
    product_name: str | None
    brand: str | None
    sodium_mg_per_100g: float | None
    ocr_text: str
    ocr_confidence: float
    ai_used: bool
    quality_warnings: list[str]


class ScoreLineOut(BaseModel):
    code: str
    label: str
    points: int
    detail: str
    ingredients: list[str] = []


class IngredientOut(BaseModel):
    display_name: str
    canonical_name: str
    position: int
    parent: str | None
    categories: list[str]
    labels: list[str]
    source: str
    is_duplicate: bool


class HighlightOut(BaseModel):
    name: str
    canonical_name: str
    position: int
    categories: list[str]
    labels: list[str]
    reason: str


class AlternativeOut(BaseModel):
    kind: Literal["swap", "tip", "history"]
    title: str
    description: str
    analysis_id: uuid.UUID | None = None
    score: int | None = None
    verdict: str | None = None


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    brand: str | None
    category: str | None
    is_saved: bool


class AnalysisSummary(BaseModel):
    id: uuid.UUID
    product: ProductBrief
    score: int
    verdict: str
    nova_group: int
    source: str
    ingredient_count: int
    created_at: datetime


class AnalysisOut(AnalysisSummary):
    raw_text: str
    sodium_mg_per_100g: float | None
    breakdown: list[ScoreLineOut]
    explanation: dict
    ingredients: list[IngredientOut]
    concerns: list[HighlightOut]
    positives: list[HighlightOut]
    alternatives: list[AlternativeOut]
    warnings: list[str]
    scoring_version: str
    knowledge_base_version: str
    ai_model: str | None
    ai_used: bool
    input_hash: str


class Page(BaseModel):
    items: list[AnalysisSummary]
    total: int
    limit: int
    offset: int


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=120)
    is_saved: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SavedProductOut(BaseModel):
    product: ProductBrief
    latest: AnalysisSummary
    notes: str | None
    saved_at: datetime | None
    analyses_count: int


class VerifyOut(BaseModel):
    analysis_id: uuid.UUID
    stored_score: int
    recomputed_score: int
    stored_verdict: str
    recomputed_verdict: str
    matches: bool
    scoring_version: str


class CompareOut(BaseModel):
    items: list[AnalysisOut]
    best_id: uuid.UUID | None
    shared_concerns: list[str]


class DashboardOut(BaseModel):
    total_analyses: int
    saved_products: int
    average_score: float | None
    verdict_counts: dict[str, int]
    recent: list[AnalysisSummary]
