from __future__ import annotations

import json

from qlib_engine.pipeline import NASDAQ100_UNIVERSE, SP500_UNIVERSE
from quant_engine.data_pipeline.market_data import initialize_cache, refresh_symbols


def main() -> None:
    initialize_cache()
    symbols = sorted(set(SP500_UNIVERSE + NASDAQ100_UNIVERSE + ["SPY", "QQQ", "XLK", "XLF", "XLE", "XLV", "XLI", "XLU", "XLRE", "XLY"]))
    result = refresh_symbols(symbols)
    print(json.dumps({"job": "market-cache-refresh", **result}))


if __name__ == "__main__":
    main()
