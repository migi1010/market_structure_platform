from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.quant_engine.sector_rotation_engine import analyze_sector_rotation

router = APIRouter(prefix="/api", tags=["sector-rotation"])


@router.get("/sector-rotation")
def sector_rotation() -> List[Dict[str, Any]]:
    try:
        return analyze_sector_rotation()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
