from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.quant_engine.stock_service import analyze_stock

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analyze")
def analyze(ticker: str = Query(..., min_length=1)) -> dict:
    try:
        return analyze_stock(ticker)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
