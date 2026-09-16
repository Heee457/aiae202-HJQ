"""Public Tencent quotes, with strict provenance and no synthetic fallback.

Endpoint: https://qt.gtimg.cn/ (GBK, tilde-separated records).
Verified positional mapping: easyquotation's upstream Tencent adapter:
https://github.com/shidenggui/easyquotation/blob/master/easyquotation/tencent.py

Field 39 is only named PE by that adapter. It is deliberately NOT labelled TTM.
The endpoint supplies market quotes, not financial reports or verified dividends.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import isfinite
import re
from threading import RLock
from time import monotonic, sleep
from urllib.parse import urlencode

import requests

from .data import StockDataError, normalize_symbol, symbol_exchange, validate_thresholds


ENDPOINT = "https://qt.gtimg.cn/"
SOURCE = "腾讯财经公开行情接口"
DEFAULT_SYMBOLS = ("600036", "600900", "600519", "300750", "688981")
SHANGHAI = timezone(timedelta(hours=8), name="Asia/Shanghai")
MAX_QUOTE_AGE = timedelta(days=7)
LIMITATIONS = [
    "仅查询配置的观察池；不代表全 A 股覆盖或投资推荐。",
    "行情可能有延迟；as_of 是来源返回的行情时间，不保证是逐笔成交时间。",
    "PE 口径未获明确确认，不能当作 TTM 市盈率；未接入股息率、行业、财报或公司风险材料。",
    "价格未经复权；报价时间超过 7 个自然日会标为 stale 并禁止参与筛选，此规则不使用交易日历。",
]
NUMBER_FIELDS = {"price": 3, "change_pct": 32, "pe_ratio": 39, "pb_ratio": 46}
MISSING_MARKERS = {"", "-", "--", "null", "none", "n/a"}
UNITS = {
    "price": "元/股", "change_pct": "%", "pe_ratio": "倍",
    "pe_ttm": "倍", "pb_ratio": "倍", "dividend_yield_pct": "%",
}


class TencentStockProvider:
    """Fetch bounded batches, cache for 60 seconds, and expose source failures."""

    def __init__(
        self, symbols=None, session=None, clock=None, cache_ttl_seconds: float = 60,
    ) -> None:
        selected = list(DEFAULT_SYMBOLS) if symbols is None else symbols
        if isinstance(selected, (str, bytes)) or not isinstance(selected, (list, tuple)):
            raise StockDataError("invalid_configuration", "STOCK_SYMBOLS 必须是用英文逗号分隔的股票代码。")
        if not 1 <= len(selected) <= 50:
            raise StockDataError("invalid_configuration", "观察池必须包含 1 到 50 个股票代码。")
        try:
            self.symbols = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in selected))
        except StockDataError:
            raise StockDataError("invalid_configuration", "观察池含空项、无效 A 股代码或不一致的交易所标记。") from None
        if (
            isinstance(cache_ttl_seconds, bool)
            or not isinstance(cache_ttl_seconds, (int, float))
            or not isfinite(cache_ttl_seconds)
            or not 0 <= cache_ttl_seconds <= 300
        ):
            raise ValueError("cache_ttl_seconds 必须是 0 到 300 之间的有限数字。")
        self.cache_ttl_seconds = cache_ttl_seconds
        self._session = session if session is not None else requests.Session()
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)
        self._cache: dict[str, dict] = {}
        self._lock = RLock()

    def metadata(self) -> dict:
        """Configuration only; this method performs no network requests."""
        return {
            "data_mode": "live",
            "scope": "watchlist",
            "scope_label": "自选关注列表",
            "source": SOURCE,
            "source_url": ENDPOINT,
            "available_metrics": ["price", "pe_ratio", "pb_ratio", "change_pct"],
            "watchlist": list(self.symbols),
            "limitations": list(LIMITATIONS),
            "cache_ttl_seconds": self.cache_ttl_seconds,
        }

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock 必须返回带时区的 datetime。")
        return now.astimezone(timezone.utc)

    @staticmethod
    def _source_url(symbols: list[str]) -> str:
        tokens = [symbol_exchange(symbol) + symbol for symbol in symbols]
        return ENDPOINT + "?" + urlencode({"q": ",".join(tokens)})

    @staticmethod
    def _number(value: str) -> float | None:
        cleaned = value.strip()
        if cleaned.lower() in MISSING_MARKERS:
            return None
        try:
            result = float(cleaned)
        except (TypeError, ValueError):
            raise StockDataError("malformed_response", "行情接口返回了无法识别的数值；请稍后重试。") from None
        if not isfinite(result):
            raise StockDataError("malformed_response", "行情接口返回了非有限数值；请稍后重试。")
        return result

    def _parse_record(self, payload: str, symbol: str, fetched_at: datetime, source_url: str) -> dict | None:
        if not payload.strip():
            return None
        fields = payload.split("~")
        if len(fields) <= 46 or fields[2] != symbol or not fields[1].strip():
            raise StockDataError("malformed_response", "行情响应字段不完整或股票代码不一致；未采用该响应。")
        if re.fullmatch(r"\d{14}", fields[30]) is None:
            raise StockDataError("malformed_response", "行情接口未提供有效的来源时间；未采用该响应。")
        try:
            quote_time = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(tzinfo=SHANGHAI)
        except ValueError:
            raise StockDataError("malformed_response", "行情接口未提供有效的来源时间；未采用该响应。") from None
        # A quote cannot legitimately be dated far beyond the successful fetch.
        if quote_time > fetched_at + timedelta(minutes=5):
            raise StockDataError("malformed_response", "来源行情时间晚于当前抓取时间，请检查系统时钟或稍后重试。")
        numbers = {key: self._number(fields[index]) for key, index in NUMBER_FIELDS.items()}
        if numbers["price"] is not None and numbers["price"] <= 0:
            numbers["price"] = None
        missing = ["pe_ttm", "dividend_yield_pct", "sector"]
        missing.extend(key for key, value in numbers.items() if value is None)
        row = {
            "symbol": symbol,
            "name": fields[1].strip(),
            **numbers,
            "pe_basis": "来源未明确PE口径",
            "pe_ttm": None,
            "dividend_yield_pct": None,
            "sector": None,
            "market": "CN-A",
            "instrument_type": "CDR" if symbol == "689009" else "A_SHARE",
            "currency": "CNY",
            "price_adjustment": "unadjusted",
            "risk_notes": [],
            "data_warnings": list(LIMITATIONS),
            "metric_units": deepcopy(UNITS),
            "missing_fields": missing,
            "as_of": quote_time.isoformat(),
            "as_of_note": "来源返回的行情时间（Asia/Shanghai），不保证是逐笔成交时间。",
            "fetched_at": fetched_at.isoformat(),
            "data_mode": "live",
            "source": SOURCE,
            "source_url": source_url,
        }
        if row["instrument_type"] == "CDR":
            row["metric_units"]["price"] = "元/份"
            row["data_warnings"].append("该证券为存托凭证，不是普通 A 股。")
        return self._with_age(row, fetched_at)

    @staticmethod
    def _with_age(row: dict, now: datetime) -> dict:
        result = deepcopy(row)
        quote_time = datetime.fromisoformat(result["as_of"])
        result["quote_status"] = "stale" if now - quote_time > MAX_QUOTE_AGE else "current"
        if result["quote_status"] == "stale":
            warning = "该报价已超过 7 个自然日，仅供查看历史信息，不能参与当前筛选。"
            if warning not in result["data_warnings"]:
                result["data_warnings"].append(warning)
        return result

    @staticmethod
    def _request_failure(exc: requests.RequestException) -> tuple[str, bool]:
        # Never include exception text: it can contain proxy credentials or bodies.
        if isinstance(exc, requests.exceptions.SSLError):
            return "TLS 证书或握手失败，请检查证书和代理设置", False
        if isinstance(exc, requests.Timeout):
            return "请求超时", True
        if isinstance(exc, requests.exceptions.ProxyError):
            return "代理连接失败，请检查代理设置", True
        if isinstance(exc, requests.ConnectionError):
            return "网络连接失败，请检查网络或代理", True
        if isinstance(exc, requests.HTTPError):
            status = exc.response.status_code if exc.response is not None else None
            if status == 429:
                # Do not repeatedly hit a rate-limited service or ignore Retry-After.
                return "HTTP 429，接口限流，请稍后重试", False
            return f"HTTP {status}" if status is not None else "HTTP 请求失败", status in {
                408, 500, 502, 503, 504,
            }
        return "网络请求异常", False

    @staticmethod
    def _remaining_time(deadline: float | None, *, delay: float = 0) -> float | None:
        remaining = None if deadline is None else deadline - monotonic()
        if remaining is not None and remaining <= delay:
            raise StockDataError(
                "refresh_timeout", "全市场更新超过时间限制，已停止请求；未返回部分市场或过期缓存。"
            ) from None
        return remaining

    def _fetch_body(self, query: str, deadline: float | None) -> str:
        for attempt in range(1, 4):
            remaining = self._remaining_time(deadline)
            # Requests applies this separately to connect/read waits, not as a
            # strict wall-clock limit. Recheck the shared deadline after the call.
            timeout = 10 if remaining is None else min(10, remaining / 2)
            try:
                response = self._session.get(ENDPOINT, params={"q": query}, timeout=timeout)
                response.raise_for_status()
                response.encoding = "gbk"
                body = response.text
            except requests.RequestException as exc:
                reason, retryable = self._request_failure(exc)
                self._remaining_time(deadline)
                if not retryable or attempt == 3:
                    raise StockDataError(
                        "source_unavailable",
                        f"真实行情接口 qt.gtimg.cn 请求失败（{reason}；尝试 {attempt} 次）。"
                        "没有回退到模拟数据或过期缓存。",
                    ) from None
                # Retry only this failed batch, leaving successful batches alone.
                self._remaining_time(deadline, delay=attempt)
                sleep(attempt)
            else:
                self._remaining_time(deadline)
                return body

    def _fetch(self, symbols: list[str], *, deadline: float | None = None) -> dict[str, dict | None]:
        query = ",".join(symbol_exchange(symbol) + symbol for symbol in symbols)
        source_url = self._source_url(symbols)
        body = self._fetch_body(query, deadline)
        fetched_at = self._now()
        # Every requested token must occur exactly once. Unexpected/partial data
        # must never masquerade as a smaller, successfully queried stock pool.
        records = re.findall(r'v_([a-z]{2}\d{6})="([^"]*)"\s*;', body)
        expected = {symbol_exchange(symbol) + symbol: symbol for symbol in symbols}
        if not records:
            raise StockDataError("malformed_response", "行情接口没有返回可识别的股票记录；请稍后重试。")
        tokens = [token for token, _ in records]
        if len(tokens) != len(set(tokens)) or set(tokens) != set(expected):
            raise StockDataError("partial_response", "行情接口返回的股票不完整或不匹配；未将部分结果当作完整股票池。")
        return {
            expected[token]: self._parse_record(payload, expected[token], fetched_at, source_url)
            for token, payload in records
        }

    def _get_quotes(self, symbols: list[str]) -> dict[str, dict | None]:
        with self._lock:
            now = self._now()
            result = {}
            needed = []
            for symbol in symbols:
                cached = self._cache.get(symbol)
                age = (now - datetime.fromisoformat(cached["fetched_at"])).total_seconds() if cached else None
                if cached is not None and 0 <= age < self.cache_ttl_seconds:
                    result[symbol] = self._with_age(cached, now)
                else:
                    needed.append(symbol)
            if needed:
                fresh = self._fetch(needed)
                # Parse the complete response before committing any cache entries.
                for symbol, row in fresh.items():
                    if row is not None:
                        self._cache[symbol] = deepcopy(row)
                    else:
                        self._cache.pop(symbol, None)
                result.update(fresh)
            return {symbol: deepcopy(result[symbol]) for symbol in symbols}

    def list_stocks(self) -> list[dict]:
        result = self._get_quotes(list(self.symbols))
        if any(row is None for row in result.values()):
            raise StockDataError("partial_response", "观察池中有股票未返回行情；请检查代码或稍后重试，未返回不完整股票池。")
        return list(result.values())

    def get_stock_details(self, symbol: str) -> dict:
        normalized = normalize_symbol(symbol)
        result = self._get_quotes([normalized])[normalized]
        if result is not None:
            return result
        return {
            "symbol": normalized,
            "error": "not_found",
            "message": "来源未返回该代码的行情；这不表示该股票不存在，可能是未覆盖或暂时无报价。",
            "data_mode": "live",
            "source": SOURCE,
            "source_url": self._source_url([normalized]),
            "fetched_at": self._now().isoformat(),
        }

    def screen_stocks(
        self, max_pe: float, min_dividend_yield_pct: float | None = None,
        sector: str | None = None,
    ) -> list[dict]:
        sector = validate_thresholds(max_pe, min_dividend_yield_pct, sector)
        if min_dividend_yield_pct is not None:
            raise StockDataError("unsupported_metric", "当前真实数据源未提供已核实的股息率，不能按股息率筛选；请删除该条件或接入分红数据源。")
        if sector is not None:
            raise StockDataError("unsupported_metric", "当前真实数据源未提供已核实的行业分类，不能按行业筛选。")
        rows = self.list_stocks()
        if any(row["quote_status"] == "stale" for row in rows):
            raise StockDataError("stale_data", "观察池含超过 7 个自然日的报价，已停止筛选；请检查来源日期或调整观察池。")
        return [
            row for row in rows
            if row["pe_ratio"] is not None and 0 < row["pe_ratio"] <= max_pe
        ]
