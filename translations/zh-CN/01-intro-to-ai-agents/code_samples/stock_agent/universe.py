"""Validate and cache the complete public Sina A-share directory.

Endpoint parameters follow AKShare's stock/cons.py. A downloaded directory is
committed only after every page, unique code, market, and final count is checked.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from threading import RLock
from tempfile import NamedTemporaryFile
import time

import requests

from .data import StockDataError, normalize_symbol, symbol_exchange


API_BASE = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center."
COUNT_URL = API_BASE + "getHQNodeStockCount"
PAGE_URL = API_BASE + "getHQNodeData"
PAGE_SIZE = 80
MIN_STOCK_COUNT = 1000
MAX_PAGES = 100
DEFAULT_CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "a_share_universe.json"
_UNSET = object()


class SinaAShareUniverse:
    """Fetch every directory page once daily; never read a demo fixture."""

    SOURCE_NAME = "新浪财经沪深京 A 股公开目录"
    SOURCE_URL = COUNT_URL + "?node=hs_a"
    PAGE_API = PAGE_URL
    CACHE_FILE = DEFAULT_CACHE
    COVERAGE_BASIS = "来源 hs_a 节点全部分页，验证数量、唯一代码和沪深京覆盖；并非交易所独立核验。"

    def __init__(self, *, session=None, clock=None, cache_ttl_seconds=86400,
                 cache_path=_UNSET):
        if (isinstance(cache_ttl_seconds, bool)
                or not isinstance(cache_ttl_seconds, (int, float))
                or not math.isfinite(cache_ttl_seconds) or cache_ttl_seconds <= 0):
            raise ValueError("cache_ttl_seconds 必须是有限正数。")
        self._session = session
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._ttl = cache_ttl_seconds
        if cache_path is _UNSET:
            cache_path = self.CACHE_FILE if session is None else None
        self._cache_path = Path(cache_path) if cache_path is not None else None
        self._symbols = None
        self._fetched_at = None
        self._exchange_counts = None
        self._cache_origin = None
        self._lock = RLock()

    def metadata(self):
        """Return provenance without a network request."""
        with self._lock:
            return deepcopy({
                "source": self.SOURCE_NAME,
                "source_url": self.SOURCE_URL,
                "page_url": self.PAGE_API,
                "fetched_at": self._fetched_at.isoformat() if self._fetched_at else None,
                "count": len(self._symbols) if self._symbols is not None else None,
                "exchange_counts": self._exchange_counts,
                "cache_ttl_seconds": self._ttl,
                "cache_origin": self._cache_origin,
                "freshness_note": "目录缓存最多保留 24 小时，新增上市股票可能在下一次目录刷新后出现。",
                "coverage_basis": self.COVERAGE_BASIS,
            })

    def _request(self, url, params):
        # Separate short-lived HTTP sessions per production worker.
        request = self._session.get if self._session is not None else requests.get
        try:
            response = request(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise StockDataError(
                "universe_unavailable", "全 A 股目录暂时不可用，请稍后重试；不会改用部分股票池。"
            ) from exc

    def _count(self):
        value = self._request(COUNT_URL, {"node": "hs_a"})
        if (isinstance(value, bool) or not isinstance(value, (str, int))
                or re.fullmatch(r"[0-9]+", str(value)) is None):
            raise StockDataError("universe_invalid", "股票目录总数格式异常，已停止全市场查询。")
        count = int(value)
        if not MIN_STOCK_COUNT <= count <= MAX_PAGES * PAGE_SIZE:
            raise StockDataError("universe_invalid", "股票目录数量超出合理范围，需检查来源或分页上限。")
        return count

    def _page(self, page):
        time.sleep(0.05)
        return self._request(PAGE_URL, {
            "page": page, "num": PAGE_SIZE, "sort": "symbol", "asc": 1,
            "node": "hs_a", "symbol": "", "_s_r_a": "page",
        })

    @staticmethod
    def _validate_tokens(rows, count):
        tokens = []
        for row in rows:
            if not isinstance(row, dict):
                raise StockDataError("universe_invalid", "股票目录记录格式异常。")
            token, code, name = row.get("symbol"), row.get("code"), row.get("name")
            if (not isinstance(token, str) or not isinstance(code, str)
                    or not isinstance(name, str) or not name.strip()
                    or re.fullmatch(r"(?:sh|sz|bj)[0-9]{6}", token) is None
                    or token[2:] != code):
                raise StockDataError("universe_invalid", "股票目录代码、名称或交易所格式异常。")
            try:
                normalize_symbol(token)
            except StockDataError as exc:
                raise StockDataError(
                    "universe_invalid", f"股票目录出现不支持的代码 {token}，需检查来源；未静默丢弃。"
                ) from exc
            tokens.append(token)
        if (len(tokens) != count or len(set(tokens)) != count
                or tokens != sorted(tokens)):
            raise StockDataError(
                "universe_incomplete", "股票目录存在重复、遗漏或分页顺序变化，请稍后重试。"
            )
        symbols = tuple(sorted(token[2:] for token in tokens))
        if len(set(symbols)) != count:
            raise StockDataError("universe_invalid", "股票目录存在跨市场重码，需检查来源。")
        exchange_counts = {exchange: sum(symbol_exchange(code) == exchange for code in symbols)
                           for exchange in ("sh", "sz", "bj")}
        if not all(exchange_counts.values()):
            raise StockDataError("universe_incomplete", "股票目录未同时覆盖沪、深、北三个交易所。")
        return symbols, exchange_counts

    def _read_cache(self, now):
        if self._cache_path is None:
            return False
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if (not isinstance(payload, dict) or payload.get("schema_version") != 1
                    or payload.get("source_url") != self.SOURCE_URL
                    or payload.get("data_mode") != "live"):
                return False
            count = payload["count"]
            if (type(count) is not int or not MIN_STOCK_COUNT <= count <= MAX_PAGES * PAGE_SIZE
                    or payload.get("verified_final_count") != count
                    or not isinstance(payload["records"], list)):
                return False
            fetched_at = datetime.fromisoformat(payload["fetched_at"])
            if fetched_at.tzinfo is None or not 0 <= (now - fetched_at).total_seconds() < self._ttl:
                return False
            symbols, exchange_counts = self._validate_tokens(payload["records"], count)
            if payload.get("exchange_counts") != exchange_counts:
                return False
        except (OSError, ValueError, TypeError, KeyError, StockDataError):
            # Bad or expired cache is never served; perform a fresh discovery.
            return False
        self._symbols, self._exchange_counts = symbols, exchange_counts
        self._fetched_at, self._cache_origin = fetched_at, "disk"
        return True

    def _write_cache(self, rows, count, fetched_at, exchange_counts):
        if self._cache_path is None:
            return
        payload = {
            "schema_version": 1, "data_mode": "live",
            "source_url": self.SOURCE_URL, "page_url": self.PAGE_API,
            "fetched_at": fetched_at.isoformat(), "count": count,
            "verified_final_count": count, "exchange_counts": exchange_counts,
            "records": [{"symbol": row["symbol"], "code": row["code"], "name": row["name"]}
                        for row in rows],
        }
        temporary = None
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tmp",
                                    prefix="universe-", dir=self._cache_path.parent,
                                    delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            temporary.replace(self._cache_path)
        except OSError as exc:
            raise StockDataError(
                "universe_cache_unwritable", "真实目录已获取，但缓存无法保存，请检查数据目录写入权限。"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def discover(self):
        """Return six-digit codes after a complete stable read or valid real cache."""
        with self._lock:
            now = self._clock()
            if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
                raise ValueError("clock 必须返回带时区的 datetime。")
            if (self._symbols is not None
                    and 0 <= (now - self._fetched_at).total_seconds() < self._ttl):
                return self._symbols
            if self._read_cache(now):
                return self._symbols
            started = time.monotonic()
            count = self._count()
            records = []
            page_numbers = list(range(1, (count + PAGE_SIZE - 1) // PAGE_SIZE + 1))
            # Four requests at most; a failed batch stops scheduling further pages.
            with ThreadPoolExecutor(max_workers=4) as executor:
                for offset in range(0, len(page_numbers), 4):
                    if time.monotonic() - started > 120:
                        raise StockDataError("universe_unavailable", "全 A 股目录下载超时，请稍后重试。")
                    batch = page_numbers[offset:offset + 4]
                    for page_number, rows in zip(batch, executor.map(self._page, batch)):
                        expected = min(PAGE_SIZE, count - (page_number - 1) * PAGE_SIZE)
                        if not isinstance(rows, list) or len(rows) != expected:
                            raise StockDataError(
                                "universe_incomplete", "股票目录分页缺失或数量不符，已停止全市场查询。"
                            )
                        records.extend(rows)
            symbols, exchange_counts = self._validate_tokens(records, count)
            if self._count() != count:
                raise StockDataError("universe_changed", "下载期间股票目录总数变化，请稍后重新查询。")
            if time.monotonic() - started > 120:
                raise StockDataError("universe_unavailable", "全 A 股目录下载超时，请稍后重试。")
            fetched_at = self._clock()
            self._write_cache(records, count, fetched_at, exchange_counts)
            self._symbols, self._exchange_counts = symbols, exchange_counts
            self._fetched_at, self._cache_origin = fetched_at, "network"
            return self._symbols
