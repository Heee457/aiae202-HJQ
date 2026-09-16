"""Whole A-share screening: verified source directory plus batched real quotes.

The directory defines coverage; page size only limits presentation. A refresh
is committed atomically, so an interrupted batch cannot become a smaller market.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
from threading import local
from time import monotonic

import requests

from .data import StockDataError, normalize_symbol, symbol_exchange, validate_thresholds
from .live_data import TencentStockProvider, SOURCE, ENDPOINT, UNITS
from .tencent_universe import TencentAShareUniverse

MARKET_LIMITATIONS = [
    "全 A 股范围按来源沪深京证券目录核对，尚未逐项与交易所上市名册独立对账。",
    "各批次行情时点不同，并非同一瞬间的全市场快照；行情可能延迟。",
    "来源 PE 口径未确认，不能称为 TTM；尚未接入股息率、行业、完整财报和新闻。",
    "无报价、缺价格、过期或缺少正市盈率的证券不能参与 PE 筛选，排除数量单独报告。",
    "过期判断使用 7 个自然日，尚未接入交易日历；按代码排列仅用于展示，不代表推荐排名。",
]


class AllAShareProvider(TencentStockProvider):
    """Discover all source-listed A shares, fetch in batches, screen before paging."""

    def __init__(self, universe=None, session=None, clock=None,
                 cache_ttl_seconds=300, batch_size=50, max_workers=4,
                 refresh_timeout_seconds=120):
        super().__init__(symbols=["600036"], session=session, clock=clock,
                         cache_ttl_seconds=cache_ttl_seconds)
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 50:
            raise ValueError("batch_size 必须在 1 到 50 之间。")
        if isinstance(max_workers, bool) or not isinstance(max_workers, int) or not 1 <= max_workers <= 4:
            raise ValueError("max_workers 必须在 1 到 4 之间。")
        if (isinstance(refresh_timeout_seconds, bool)
                or not isinstance(refresh_timeout_seconds, (int, float))
                or not 1 <= refresh_timeout_seconds <= 180):
            raise ValueError("refresh_timeout_seconds 必须在 1 到 180 之间。")
        self.universe = universe if universe is not None else TencentAShareUniverse()
        self.symbols = ()
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.refresh_timeout_seconds = refresh_timeout_seconds
        self._injected_session = session
        self._thread_sessions = local()
        self._market_rows = None
        self._market_fetched_at = None
        self._coverage = None
        self._exclusions = None

    def metadata(self):
        return {
            "data_mode": "live", "scope": "all_a",
            "scope_label": "全 A 股（沪深京，按来源证券目录）",
            "source": SOURCE, "source_url": ENDPOINT,
            "universe_source": self.universe.metadata().get("source", "沪深京 A 股目录"),
            "universe": self.universe.metadata(),
            "available_metrics": ["price", "pe_ratio", "pb_ratio", "change_pct"],
            "watchlist": [],
            "coverage": deepcopy(self._coverage),
            "screening_exclusions": deepcopy(self._exclusions),
            "limitations": list(MARKET_LIMITATIONS),
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    @staticmethod
    def _exclude_counts(rows):
        counts = {"unavailable": 0, "stale": 0, "missing_price": 0,
                  "missing_or_nonpositive_pe": 0, "eligible_count": 0}
        for row in rows:
            if row["quote_status"] == "unavailable":
                counts["unavailable"] += 1
            elif row["quote_status"] == "stale":
                counts["stale"] += 1
            elif row["price"] is None:
                counts["missing_price"] += 1
            elif row["pe_ratio"] is None or row["pe_ratio"] <= 0:
                counts["missing_or_nonpositive_pe"] += 1
            else:
                counts["eligible_count"] += 1
        return counts

    def _unavailable(self, symbol, fetched_at):
        return {
            "symbol": symbol, "name": None, "price": None, "pe_ratio": None,
            "pb_ratio": None, "change_pct": None, "pe_ttm": None, "sector": None,
            "dividend_yield_pct": None, "pe_basis": "来源未明确PE口径",
            "market": "CN-A", "currency": "CNY", "data_mode": "live",
            "source": SOURCE, "source_url": self._source_url([symbol]),
            "as_of": None, "fetched_at": fetched_at.isoformat(),
            "quote_status": "unavailable", "price_adjustment": "unadjusted",
            "risk_notes": [], "metric_units": deepcopy(UNITS),
            "missing_fields": ["name", "price", "pe_ratio", "pb_ratio", "change_pct",
                               "pe_ttm", "sector", "dividend_yield_pct", "as_of"],
            "data_warnings": list(MARKET_LIMITATIONS) + ["目录含此代码，行情接口未提供报价。"],
        }

    def _fetch_batch(self, batch, deadline):
        if monotonic() >= deadline:
            raise StockDataError("refresh_timeout", "全市场更新超过时间限制，未将部分数据作为完整结果。")
        # One session per worker avoids sharing mutable HTTP state across threads.
        session = self._injected_session
        if session is None:
            session = getattr(self._thread_sessions, "session", None)
            if session is None:
                session = self._thread_sessions.session = requests.Session()
        parser = TencentStockProvider(symbols=batch, session=session, clock=self._clock)
        try:
            return parser._fetch(batch, deadline=deadline)
        except StockDataError as exc:
            raise StockDataError(
                exc.code,
                f"{exc.message} 失败批次：{batch[0]}—{batch[-1]}，共 {len(batch)} 只；"
                "本次全市场更新未完成。",
            ) from None

    def _aged_rows(self, now):
        return [
            self._with_age(row, now) if row["as_of"] is not None else deepcopy(row)
            for row in self._market_rows
        ]

    def list_stocks(self):
        with self._lock:
            now = self._now()
            age = ((now - self._market_fetched_at).total_seconds()
                   if self._market_fetched_at is not None else None)
            if self._market_rows is not None and 0 <= age < self.cache_ttl_seconds:
                rows = self._aged_rows(now)
                self._exclusions = self._exclude_counts(rows)
                return rows
            self._coverage = None
            self._exclusions = None
            started_at = now.isoformat()
            symbols = tuple(self.universe.discover())
            if not symbols or len(symbols) != len(set(symbols)):
                raise StockDataError("incomplete_universe", "全市场证券目录为空或重复，已停止查询。")
            if any(normalize_symbol(symbol) != symbol for symbol in symbols):
                raise StockDataError("incomplete_universe", "全市场证券目录代码格式无效。")
            directory = self.universe.metadata()
            if directory.get("count") != len(symbols):
                raise StockDataError("incomplete_universe", "目录声明的数量与实际证券数量不一致。")
            batches = [list(symbols[i:i + self.batch_size])
                       for i in range(0, len(symbols), self.batch_size)]
            fetched = {}
            deadline = monotonic() + self.refresh_timeout_seconds
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            futures = []
            try:
                futures = [executor.submit(self._fetch_batch, batch, deadline) for batch in batches]
                for future in as_completed(futures, timeout=self.refresh_timeout_seconds):
                    fetched.update(future.result())
            except TimeoutError:
                raise StockDataError("refresh_timeout", "全市场更新超时，未返回部分市场或过期缓存。") from None
            finally:
                for future in futures:
                    future.cancel()
                executor.shutdown(wait=True, cancel_futures=True)
            if set(fetched) != set(symbols):
                raise StockDataError("partial_response", "全市场行情未覆盖全部目录代码，已停止筛选。")
            completed = self._now()
            rows = []
            for symbol in sorted(symbols):
                row = fetched[symbol]
                if row is None:
                    row = self._unavailable(symbol, completed)
                else:
                    row = self._with_age(row, completed)
                    row["source_url"] = self._source_url([symbol])
                    row["data_warnings"] = list(MARKET_LIMITATIONS) + (
                        ["该报价超过 7 个自然日，已排除当前筛选。"] if row["quote_status"] == "stale" else [])
                rows.append(row)
            counts = {exchange: sum(symbol_exchange(s) == exchange for s in symbols)
                      for exchange in ("sh", "sz", "bj")}
            unavailable = sum(row["quote_status"] == "unavailable" for row in rows)
            # No shared state from an incomplete refresh reaches these assignments.
            self.symbols = tuple(sorted(symbols))
            self._market_rows = deepcopy(rows)
            self._market_fetched_at = completed
            self._cache = {row["symbol"]: deepcopy(row) for row in rows
                           if row["quote_status"] != "unavailable"}
            self._coverage = {
                "source_count": directory.get("source_count", len(symbols)),
                "excluded_instruments": deepcopy(directory.get("excluded_instruments", [])),
                "expected_count": len(symbols), "received_count": len(rows),
                "quoted_count": len(rows) - unavailable, "unavailable_count": unavailable,
                "exchange_counts": counts, "complete": True,
                "snapshot_started_at": started_at, "snapshot_completed_at": completed.isoformat(),
                "universe_fetched_at": directory.get("fetched_at"),
            }
            self._exclusions = self._exclude_counts(rows)
            return deepcopy(rows)

    def get_stock_details(self, symbol):
        normalized = normalize_symbol(symbol)
        with self._lock:
            if normalized == "689009":
                raise StockDataError("unsupported_instrument", "689009 是存托凭证，不属于当前普通 A 股研究范围。")
            now = self._now()
            age = ((now - self._market_fetched_at).total_seconds()
                   if self._market_fetched_at else None)
            if self._market_rows is not None and 0 <= age < self.cache_ttl_seconds:
                row = next((row for row in self._market_rows if row["symbol"] == normalized), None)
                if row is not None:
                    return self._with_age(row, now) if row["as_of"] else deepcopy(row)
            row = super().get_stock_details(normalized)
            if "data_warnings" in row:
                row["data_warnings"] = list(MARKET_LIMITATIONS)
            return row

    def screen_stocks(self, max_pe, min_dividend_yield_pct=None, sector=None):
        sector = validate_thresholds(max_pe, min_dividend_yield_pct, sector)
        if min_dividend_yield_pct is not None:
            raise StockDataError("unsupported_metric", "当前未接入已核实的股息率，不能按股息率筛选全 A 股。")
        if sector is not None:
            raise StockDataError("unsupported_metric", "当前未接入已核实的行业分类，不能按行业筛选全 A 股。")
        rows = self.list_stocks()
        return [row for row in rows if row["quote_status"] == "current"
                and row["price"] is not None and row["pe_ratio"] is not None
                and 0 < row["pe_ratio"] <= max_pe]
