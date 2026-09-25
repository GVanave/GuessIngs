import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.errors import AppError
from app.core.ratelimit import rate_limit
from app.models import Analysis, Product, User
from app.schemas import AnalysisOut, AnalyzeIn, CompareOut, DashboardOut, Page, VerifyOut
from app.services import analysis as svc

router = APIRouter(tags=["analyses"])


def _load(db: Session, user: User, analysis_id: uuid.UUID) -> Analysis:
    row = db.execute(
        select(Analysis)
        .options(selectinload(Analysis.ingredients), selectinload(Analysis.product))
        .where(Analysis.id == analysis_id, Analysis.user_id == user.id)
    ).scalar_one_or_none()
    if row is None:  # also returned for other users' analyses (no existence leak)
        raise AppError(404, "not_found", "That analysis doesn't exist or was deleted.")
    return row


@router.post("/analyses", response_model=AnalysisOut, status_code=201,
             dependencies=[Depends(rate_limit("analyze", "rate_limit_analyze_per_minute"))])
async def create_analysis(body: AnalyzeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = await run_in_threadpool(
        svc.run_analysis, db, user, body.ingredients_text, body.product_name, body.brand,
        body.sodium_mg_per_100g, body.source, body.ocr_text,
    )
    return svc.detail(db, analysis)


@router.get("/analyses", response_model=Page)
def list_analyses(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    verdict: str | None = Query(None, pattern="^(GREEN|YELLOW|RED)$"),
    q: str | None = Query(None, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Analysis).join(Product).where(Analysis.user_id == user.id)
    if verdict:
        stmt = stmt.where(Analysis.verdict == verdict)
    if q:
        like = f"%{q.lower().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(or_(func.lower(Product.name).like(like), func.lower(func.coalesce(Product.brand, "")).like(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.options(selectinload(Analysis.ingredients), selectinload(Analysis.product))
        .order_by(Analysis.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return {"items": [svc.summary(a) for a in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.detail(db, _load(db, user, analysis_id))


@router.get("/analyses/{analysis_id}/verify", response_model=VerifyOut)
def verify_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _load(db, user, analysis_id)
    result = svc.rescore(analysis)
    return {
        "analysis_id": analysis.id,
        "stored_score": analysis.score,
        "recomputed_score": result.score,
        "stored_verdict": analysis.verdict,
        "recomputed_verdict": result.verdict.value,
        "matches": result.score == analysis.score and result.verdict.value == analysis.verdict,
        "scoring_version": result.scoring_version,
    }


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = _load(db, user, analysis_id)
    product = analysis.product
    db.delete(analysis)
    db.flush()
    remaining = db.execute(select(func.count()).where(Analysis.product_id == product.id)).scalar_one()
    if remaining == 0 and not product.is_saved:
        db.delete(product)
    db.commit()
    return Response(status_code=204)


@router.get("/compare", response_model=CompareOut)
def compare(
    ids: list[uuid.UUID] = Query(..., min_length=2, max_length=4),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    unique = list(dict.fromkeys(ids))
    if len(unique) < 2:
        raise AppError(422, "compare_needs_two", "Choose at least two different products to compare.")
    details = [svc.detail(db, _load(db, user, i)) for i in unique]
    best = max(details, key=lambda d: (d["score"], -len(d["concerns"])))
    tie = sum(1 for d in details if d["score"] == best["score"]) > 1
    concern_sets = [{c["canonical_name"] for c in d["concerns"]} for d in details]
    shared = sorted(set.intersection(*concern_sets)) if concern_sets else []
    return {"items": details, "best_id": None if tie else best["id"], "shared_concerns": shared}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.execute(select(func.count()).where(Analysis.user_id == user.id)).scalar_one()
    avg = db.execute(select(func.avg(Analysis.score)).where(Analysis.user_id == user.id)).scalar_one()
    counts = dict(
        db.execute(select(Analysis.verdict, func.count()).where(Analysis.user_id == user.id).group_by(Analysis.verdict)).all()
    )
    saved = db.execute(select(func.count()).where(Product.user_id == user.id, Product.is_saved.is_(True))).scalar_one()
    recent = db.execute(
        select(Analysis).options(selectinload(Analysis.ingredients), selectinload(Analysis.product))
        .where(Analysis.user_id == user.id).order_by(Analysis.created_at.desc()).limit(5)
    ).scalars().all()
    return {
        "total_analyses": total,
        "saved_products": saved,
        "average_score": round(float(avg), 1) if avg is not None else None,
        "verdict_counts": {v: int(counts.get(v, 0)) for v in ("GREEN", "YELLOW", "RED")},
        "recent": [svc.summary(a) for a in recent],
    }
