from __future__ import annotations

import json
import sys
from typing import Any, Dict

from backend.quant_engine.stock_service import analyze_stock
from backend.quant_engine.qlib_engine import run_alpha_ranking


class ProductionPipeline:
    def run_full_pipeline(self) -> Dict[str, Any]:
        return run_alpha_ranking("sp500")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print(json.dumps(analyze_stock(symbol), ensure_ascii=False, indent=2))
