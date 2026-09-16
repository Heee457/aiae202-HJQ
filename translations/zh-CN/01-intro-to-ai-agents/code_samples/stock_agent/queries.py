"""Shared full-scope queries with bounded presentation for tools and HTTP."""

from copy import deepcopy

from .data import StockDataError, StockProvider


MAX_PAGE_SIZE = 100
SORT_DESCRIPTION = "先在完整数据范围筛选，再按六位股票代码升序分页；展示次序不代表投资排名。"
PAGE_FIELDS = (
    "symbol", "name", "exchange", "instrument_type", "price", "pe_ratio", "pe_basis", "pb_ratio",
    "change_pct", "dividend_yield_pct", "sector", "metric_units", "data_mode",
    "source", "source_url", "as_of", "fetched_at", "quote_status",
    "missing_fields", "data_warnings",
)


def validate_pagination(limit: int, offset: int) -> None:
    """Reject ambiguous page sizes before making a network request."""
    if (
        isinstance(limit, bool) or not isinstance(limit, int)
        or not 1 <= limit <= MAX_PAGE_SIZE
        or isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
    ):
        raise StockDataError(
            "invalid_pagination", "每页条数 limit 必须是 1—100 的整数，offset 必须是大于等于 0 的整数。"
        )


def _scope_metadata(provider: StockProvider, row_count: int) -> dict:
    """Retain coverage evidence; legacy demo providers describe their own pool."""
    metadata = deepcopy(provider.metadata())
    scope = metadata.get("scope", "watchlist")
    metadata.setdefault("scope", scope)
    metadata.setdefault("scope_label", "全 A 股" if scope == "all_a" else "配置的股票范围")
    metadata.setdefault("coverage", {
        "expected_count": row_count,
        "received_count": row_count,
        "complete": scope != "all_a",
    })
    return metadata


def market_summary(provider: StockProvider) -> dict:
    """Fetch the full scope, then return counts and provenance without all rows."""
    rows = provider.list_stocks()
    metadata = _scope_metadata(provider, len(rows))
    return {
        **metadata,
        "total": len(rows),
        "universe_count": len(rows),
        "sort_description": SORT_DESCRIPTION,
    }


def stock_page(
    provider: StockProvider, limit: int = 20, offset: int = 0,
    max_pe: float | None = None, min_dividend_yield_pct: float | None = None,
    sector: str | None = None,
) -> dict:
    """Screen the complete scope first; paginate only the displayed result."""
    validate_pagination(limit, offset)
    if max_pe is None:
        if min_dividend_yield_pct is not None or sector is not None:
            raise StockDataError("invalid_filters", "筛选需要提供市盈率上限 max_pe。")
        rows = provider.list_stocks()
        universe_count = len(rows)
    else:
        # The provider applies filters to its entire scope, never this page.
        rows = provider.screen_stocks(max_pe, min_dividend_yield_pct, sector)
        coverage = provider.metadata().get("coverage") or {}
        universe_count = coverage.get("received_count")
        if not isinstance(universe_count, int) or isinstance(universe_count, bool):
            universe_count = len(provider.list_stocks())
    metadata = _scope_metadata(provider, universe_count)
    ordered = sorted(rows, key=lambda row: row["symbol"])
    items = [
        {key: deepcopy(row[key]) for key in PAGE_FIELDS if key in row}
        for row in ordered[offset:offset + limit]
    ]
    return {
        "items": items,
        "total": len(ordered),
        "universe_count": universe_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < len(ordered),
        "coverage": metadata["coverage"],
        "scope": metadata["scope"],
        "scope_label": metadata["scope_label"],
        "sort_description": SORT_DESCRIPTION,
        "metadata": metadata,
    }