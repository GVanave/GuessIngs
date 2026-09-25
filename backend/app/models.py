"""SQLAlchemy ORM models.

Every analysis stores the exact structured inputs to the scoring engine (the
classified ingredients with positions and categories), the sodium value, the
score breakdown and the versions of the scoring rules, knowledge base and AI
model used — so any analysis can be re-scored and verified later.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict] = mapped_column(JSONType, default=dict)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    products: Mapped[list[Product]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analyses: Mapped[list[Analysis]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="products")
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="Analysis.created_at.desc()"
    )


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)

    source: Mapped[str] = mapped_column(String(20))  # manual | upload | camera
    raw_text: Mapped[str] = mapped_column(Text)  # ingredient text that was scored
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    sodium_mg_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)

    score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[str] = mapped_column(String(10), index=True)
    nova_group: Mapped[int] = mapped_column(Integer)
    breakdown: Mapped[list] = mapped_column(JSONType)
    explanation: Mapped[dict] = mapped_column(JSONType, default=dict)
    alternatives: Mapped[list] = mapped_column(JSONType, default=list)
    warnings: Mapped[list] = mapped_column(JSONType, default=list)

    scoring_version: Mapped[str] = mapped_column(String(20))
    knowledge_base_version: Mapped[str] = mapped_column(String(40))
    ai_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="analyses")
    product: Mapped[Product] = relationship(back_populates="analyses")
    ingredients: Mapped[list[AnalysisIngredient]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan", order_by="AnalysisIngredient.order_index"
    )


class Ingredient(Base):
    """Global classification cache: one row per canonical ingredient name.

    Knowledge-base and pattern classifications are deterministic; AI
    classifications are stored here the first time they are made so that the
    same ingredient is always classified identically afterwards.
    """

    __tablename__ = "ingredients"
    __table_args__ = (UniqueConstraint("name", name="uq_ingredients_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    canonical_name: Mapped[str] = mapped_column(String(160))
    categories: Mapped[list] = mapped_column(JSONType)
    source: Mapped[str] = mapped_column(String(20))  # kb | pattern | ai
    classifier_version: Mapped[str] = mapped_column(String(80))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalysisIngredient(Base):
    __tablename__ = "analysis_ingredients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer)
    display_name: Mapped[str] = mapped_column(String(200))
    canonical_name: Mapped[str] = mapped_column(String(160))
    parent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    categories: Mapped[list] = mapped_column(JSONType)
    source: Mapped[str] = mapped_column(String(20))
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    analysis: Mapped[Analysis] = relationship(back_populates="ingredients")
