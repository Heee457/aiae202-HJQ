"""Stock-provider contract, explicit demo fixtures, and real-data configuration."""

from copy import deepcopy
import json
from math import isfinite
import os
from pathlib import Path
import re
from typing import Protocol

from dotenv import load_dotenv


class StockDataError(RuntimeError):
    """A safe, actionable data error; provider response bodies are never exposed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class StockProvider(Protocol):
    """Providers return independent JSON-compatible records with provenance."""

    def metadata(self) -> dict:
        ...

    def list_stocks(self) -> list[dict]:
        ...

    def get_stock_details(self, symbol: str) -> dict:
        ...

    def screen_stocks(
        self, max_pe: float, min_dividend_yield_pct: float | None = None,
        sector: str | None = None,
    ) -> list[dict]:
        ...


def normalize_symbol(symbol: str) -> str:
    """Accept a six-digit A-share code, sh600036, or 600036.SH; reject indices."""
    if not isinstance(symbol, str):
        raise StockDataError("invalid_symbol", "股票代码必须是字符串。")
    match = re.fullmatch(r"(?:(sh|sz|bj))?(\d{6})(?:\.(sh|sz|bj))?", symbol.strip(), re.I)
    if not match:
        raise StockDataError("invalid_symbol", "请提供六位 A 股代码，例如 600036、sh600036 或 600036.SH。")
    prefix, code, suffix = match.groups()
    exchange = symbol_exchange(code)
    if any(value and value.lower() != exchange for value in (prefix, suffix)):
        raise StockDataError("invalid_symbol", "股票代码与交易所标记不一致。")
    return code


def symbol_exchange(symbol: str) -> str:
    """Validate a supported stock-code range, not actual listing membership."""
    if re.fullmatch(r"(600|601|603|605|688|689)\d{3}", symbol):
        return "sh"
    # SZSE issuer disclosure confirms the renamed listing 302132 (formerly 300114).
    # https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-06-09/9e9ccc82-e096-48d0-872c-e660a807f4ac.PDF
    if symbol == "302132" or re.fullmatch(r"(000|001|002|003|300|301)\d{3}", symbol):
        return "sz"
    if re.fullmatch(r"(43|83|87|88|92)\d{4}", symbol):
        return "bj"
    raise StockDataError("invalid_symbol", "该代码不属于支持的沪、深、北 A 股代码范围；不支持指数、基金或 B 股。")


def validate_thresholds(
    max_pe: float, min_dividend_yield_pct: float | None = None,
    sector: str | None = None,
) -> str | None:
    """Validate numeric filter inputs; dividend None means no dividend filter."""
    values = [("max_pe", max_pe)]
    if min_dividend_yield_pct is not None:
        values.append(("min_dividend_yield_pct", min_dividend_yield_pct))
    for name, value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} 必须是有限数字。")
    if max_pe <= 0:
        raise ValueError("max_pe 必须大于 0。")
    if min_dividend_yield_pct is not None and not 0 <= min_dividend_yield_pct <= 100:
        raise ValueError("min_dividend_yield_pct 必须在 0 到 100 之间，单位为百分数。")
    if sector is not None and not isinstance(sector, str):
        raise ValueError("sector 必须是行业名称字符串或 None。")
    return (sector.strip() or None) if sector is not None else None


class DemoStockProvider:
    """Read fixed invented teaching fixtures, only when explicitly selected."""

    def __init__(self) -> None:
        path = Path(__file__).resolve().parents[1] / "data" / "stocks.demo.json"
        dataset = json.loads(path.read_text(encoding="utf-8"))
        self._metadata = dataset["metadata"]
        self._metadata["metric_units"]["pe_ratio"] = "倍"
        self._stocks = [
            {**deepcopy(self._metadata), **stock, "pe_ratio": stock["pe_ttm"],
             "pe_basis": "教学模拟 TTM 市盈率"}
            for stock in dataset["stocks"]
        ]

    def metadata(self) -> dict:
        return {
            "data_mode": "demo",
            "scope": "watchlist",
            "scope_label": "教学观察池",
            "source": self._metadata["source"],
            "available_metrics": ["price", "pe_ratio", "pe_ttm", "dividend_yield_pct", "sector"],
            "watchlist": [stock["symbol"] for stock in self._stocks],
            "limitations": ["全部数值为人工构造的教学模拟数据，不代表任何日期的真实行情。"],
            "cache_ttl_seconds": 0,
        }

    def list_stocks(self) -> list[dict]:
        return deepcopy(self._stocks)

    def get_stock_details(self, symbol: str) -> dict:
        symbol = symbol.strip()
        for stock in self._stocks:
            if stock["symbol"] == symbol:
                return deepcopy(stock)
        return {
            **deepcopy(self._metadata),
            "symbol": symbol,
            "error": "not_found",
            "message": "该代码不在教学股票池中；这不表示股票不存在。请查询股票池或选择真实数据模式。",
        }

    def screen_stocks(
        self, max_pe: float, min_dividend_yield_pct: float | None = None,
        sector: str | None = None,
    ) -> list[dict]:
        sector = validate_thresholds(max_pe, min_dividend_yield_pct, sector)
        matches = []
        for stock in self._stocks:
            pe = stock["pe_ttm"]
            dividend = stock["dividend_yield_pct"]
            if pe is None or pe <= 0:
                continue
            if min_dividend_yield_pct is not None and (
                dividend is None or dividend < min_dividend_yield_pct
            ):
                continue
            if sector and stock["sector"] != sector:
                continue
            if pe <= max_pe:
                matches.append(stock)
        return deepcopy(matches)


def load_stock_environment() -> None:
    """Local sample .env takes precedence over root .env; exported values win."""
    samples = Path(__file__).resolve().parents[1]
    load_dotenv(samples / ".env", override=False)
    root = next(
        (path for path in samples.parents
         if (path / "scripts" / "validate_notebooks.py").is_file()),
        None,
    )
    if root is not None:
        load_dotenv(root / ".env", override=False)


def create_provider(mode: str | None = None) -> StockProvider:
    """Default to public real quotes; never fall back to demo after an error."""
    load_stock_environment()
    selected = mode if mode is not None else os.environ.get("STOCK_DATA_MODE", "live")
    if not isinstance(selected, str) or selected.strip().lower() not in {"live", "demo"}:
        raise StockDataError("invalid_configuration", "STOCK_DATA_MODE 必须为 live 或 demo。")
    if selected.strip().lower() == "demo":
        return DemoStockProvider()
    scope = os.environ.get("STOCK_SCOPE", "all_a").strip().lower()
    if scope == "all_a":
        from .market_data import AllAShareProvider

        return AllAShareProvider()
    if scope == "watchlist":
        from .live_data import TencentStockProvider

        configured = os.environ.get("STOCK_SYMBOLS")
        symbols = configured.split(",") if configured is not None else None
        return TencentStockProvider(symbols=symbols)
    raise StockDataError("invalid_configuration", "STOCK_SCOPE 必须为 all_a（全 A 股）或 watchlist（关注列表）。")
