import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import AppError
from app.models import Analysis, Product, User, utcnow
from app.schemas import ProductBrief, ProductUpdate, SavedProductOut
from app.services import analysis as svc

router = APIRouter(prefix="/products", tags=["products"])


def _load(db: Session, user: User, product_id: uuid.UUID) -> Product:
    product = db.execute(
        select(Product)
        .options(selectinload(Product.analyses).selectinload(Analysis.ingredients))
        .where(Product.id == product_id, Product.user_id == user.id)
    ).scalar_one_or_none()
    if product is None:
        raise AppError(404, "not_found", "That product doesn't exist or was deleted.")
    return product


@router.get("/saved", response_model=list[SavedProductOut])
def saved_products(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.execute(
        select(Product)
        .options(selectinload(Product.analyses).selectinload(Analysis.ingredients))
        .where(Product.user_id == user.id, Product.is_saved.is_(True))
        .order_by(Product.saved_at.desc())
    ).scalars().all()
    out = []
    for p in products:
        if not p.analyses:
            continue
        out.append({
            "product": p,
            "latest": svc.summary(p.analyses[0]),
            "notes": p.notes,
            "saved_at": p.saved_at,
            "analyses_count": len(p.analyses),
        })
    return out


@router.patch("/{product_id}", response_model=ProductBrief)
def update_product(product_id: uuid.UUID, body: ProductUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    product = _load(db, user, product_id)
    if body.name is not None:
        product.name = " ".join(body.name.split())
    if body.brand is not None:
        product.brand = " ".join(body.brand.split()) or None
    if body.notes is not None:
        product.notes = body.notes.strip() or None
    if body.is_saved is not None and body.is_saved != product.is_saved:
        product.is_saved = body.is_saved
        product.saved_at = utcnow() if body.is_saved else None
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_load(db, user, product_id))
    db.commit()
    return Response(status_code=204)
