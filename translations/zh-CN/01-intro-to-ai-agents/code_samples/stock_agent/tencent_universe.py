"""Complete Tencent aStock directory with public-source provenance.

Parameters follow AKShare stock/stock_zh_a_tx.py. The endpoint sorts by price,
so uniqueness and stable total counts are required before committing a snapshot.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import re
import time

from .data import StockDataError, symbol_exchange
from .universe import SinaAShareUniverse


TENCENT_DIRECTORY_URL = "https://proxy.finance.qq.com/cgi/cgi-bin/rank/hs/getBoardRankList"
PAGE_SIZE = 200
MIN_STOCK_COUNT = 1000
MAX_STOCK_COUNT = 8000


class TencentAShareUniverse(SinaAShareUniverse):
    """Use every aStock page covering all three exchanges, cached for 24 hours."""

    SOURCE_NAME = "腾讯财经沪深京 A 股公开目录"
    SOURCE_URL = TENCENT_DIRECTORY_URL + "?board_code=aStock"
    PAGE_API = TENCENT_DIRECTORY_URL
    CACHE_FILE = SinaAShareUniverse.CACHE_FILE.with_name("tencent_a_share_universe.json")
    COVERAGE_BASIS = "来源 aStock 节点全部分页，验证数量、唯一代码和沪深京覆盖，再明确排除已核实的存托凭证；并非交易所独立核验。"
    EXCLUDED_INSTRUMENTS = ({
        "symbol": "689009", "name": "九号公司-WD", "instrument_type": "CDR",
        "reason": "存托凭证不属于普通 A 股筛选范围",
        "source_url": "https://www.sse.com.cn/disclosure/announcement/listing/c/c_20201027_5242851.shtml",
    },)

    def metadata(self):
        """Disclose both the complete source directory and ordinary A-share scope."""
        with self._lock:
            result = super().metadata()
            result["source_count"] = result["count"]
            result["source_exchange_counts"] = result["exchange_counts"]
            result["excluded_instruments"] = []
            if self._symbols is not None:
                excluded = [dict(item) for item in self.EXCLUDED_INSTRUMENTS
                            if item["symbol"] in self._symbols]
                excluded_codes = {item["symbol"] for item in excluded}
                selected = [code for code in self._symbols if code not in excluded_codes]
                result["count"] = len(selected)
                result["exchange_counts"] = {
                    exchange: sum(symbol_exchange(code) == exchange for code in selected)
                    for exchange in ("sh", "sz", "bj")
                }
                result["excluded_instruments"] = excluded
            return result

    def discover(self):
        """Return ordinary A shares; retain the complete source directory in cache."""
        raw_symbols = self._discover_directory()
        excluded = {item["symbol"] for item in self.EXCLUDED_INSTRUMENTS}
        return tuple(code for code in raw_symbols if code not in excluded)

    def _fetch_page(self, offset):
        time.sleep(0.05)
        payload = self._request(TENCENT_DIRECTORY_URL, {
            "_appver": "11.17.0", "board_code": "aStock", "sort_type": "price",
            "direct": "down", "offset": str(offset), "count": str(PAGE_SIZE),
        })
        if (not isinstance(payload, dict) or type(payload.get("code")) is not int
                or payload["code"] != 0):
            raise StockDataError("universe_invalid", "腾讯股票目录响应状态异常。")
        content = payload.get("data")
        if not isinstance(content, dict):
            raise StockDataError("universe_invalid", "腾讯股票目录响应格式异常。")
        total, actual_offset = content.get("total"), content.get("offset")
        if (isinstance(total, bool) or not isinstance(total, (int, str))
                or re.fullmatch(r"[0-9]+", str(total)) is None
                or not MIN_STOCK_COUNT <= int(total) <= MAX_STOCK_COUNT
                or isinstance(actual_offset, bool)
                or not isinstance(actual_offset, (int, str))
                or str(actual_offset) != str(offset)):
            raise StockDataError("universe_invalid", "腾讯股票目录数量或分页位置异常。")
        rows = content.get("rank_list")
        expected = min(PAGE_SIZE, int(total) - offset)
        if not isinstance(rows, list) or expected < 1 or len(rows) != expected:
            raise StockDataError("universe_incomplete", "腾讯股票目录分页缺失，已停止全市场查询。")
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                raise StockDataError("universe_invalid", "腾讯股票目录记录格式异常。")
            token = row.get("code")
            if (not isinstance(token, str)
                    or re.fullmatch(r"(?:sh|sz|bj)[0-9]{6}", token) is None):
                raise StockDataError("universe_invalid", "腾讯股票目录代码格式异常。")
            normalized.append({"symbol": token, "code": token[2:], "name": row.get("name")})
        return int(total), normalized

    def _discover_directory(self):
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
            count, records = self._fetch_page(0)
            offsets = list(range(PAGE_SIZE, count, PAGE_SIZE))
            with ThreadPoolExecutor(max_workers=4) as executor:
                for start in range(0, len(offsets), 4):
                    if time.monotonic() - started > 120:
                        raise StockDataError("universe_unavailable", "腾讯全 A 股目录下载超时，请稍后重试。")
                    batch = offsets[start:start + 4]
                    for page_count, rows in executor.map(self._fetch_page, batch):
                        if page_count != count:
                            raise StockDataError("universe_changed", "下载期间股票目录总数变化，请稍后重试。")
                        records.extend(rows)
            # Price ordering can change during trading; never silently deduplicate.
            records.sort(key=lambda row: row["symbol"])
            symbols, exchange_counts = self._validate_tokens(records, count)
            final_count, _ = self._fetch_page(0)
            if final_count != count:
                raise StockDataError("universe_changed", "下载期间股票目录总数变化，请稍后重试。")
            if time.monotonic() - started > 120:
                raise StockDataError("universe_unavailable", "腾讯全 A 股目录下载超时，请稍后重试。")
            fetched_at = self._clock()
            self._write_cache(records, count, fetched_at, exchange_counts)
            self._symbols, self._exchange_counts = symbols, exchange_counts
            self._fetched_at, self._cache_origin = fetched_at, "network"
            return self._symbols
