import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Store, KLINE_COLUMNS


def _get_default_store_dir() -> Path:
    """获取默认缓存目录"""
    try:
        from fine.config import get_config
        return get_config().get_store_dir()
    except Exception:
        import platformdirs
        return Path(platformdirs.user_config_dir("fine")) / ".store"


class CSVStore(Store):
    """CSV file-based store with structured data support

    Usage:
        store = CSVStore()
        store.set("key", {"data": "value"})
        value = store.get("key")

        # Structured kline data
        store.save_kline("茅台", "sh600519", "1d", 1800.0, 1850.0, 1860.0, 1790.0, 1000000)
        klines = store.query_klines(symbol="sh600519", period="1d")
    """

    def __init__(self, store_dir: Optional[str] = None):
        if store_dir:
            self.store_dir = Path(store_dir)
        else:
            self.store_dir = _get_default_store_dir()
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _parse_key(self, key: str) -> Dict[str, str]:
        """解析缓存 key: kline:{provider}:{symbol}:{period}:{start}:{end}"""
        parts = key.split(":")
        if len(parts) >= 6 and parts[0] == "kline":
            return {
                "provider": parts[1],
                "symbol": parts[2],
                "period": parts[3],
                "start_date": parts[4],
                "end_date": parts[5],
            }
        return {}

    def _get_store_path(self, key: str) -> Path:
        parsed = self._parse_key(key)
        if parsed:
            symbol = parsed.get("symbol", "")
            period = parsed.get("period", "")
            start = parsed.get("start_date", "")
            end = parsed.get("end_date", "")
            return self.store_dir / f"{symbol}_{period}_{start}_{end}.csv"
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.store_dir / f"{safe_key}.csv"

    def _get_kline_path(self, symbol: str) -> Path:
        return self.store_dir / f"{symbol}.csv"

    def get(self, key: str) -> Optional[Any]:
        store_path = self._get_store_path(key)
        if not store_path.exists():
            return None

        try:
            with open(store_path, "r", encoding="utf-8") as f:
                content = f.read()
                return json.loads(content) if content else []
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        store_path = self._get_store_path(key)

        if isinstance(value, (list, dict)):
            with open(store_path, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)

    def delete(self, key: str) -> bool:
        store_path = self._get_store_path(key)
        if store_path.exists():
            store_path.unlink()
            return True
        return False

    def clear(self) -> None:
        for csv_file in self.store_dir.glob("*.csv"):
            csv_file.unlink()

    def exists(self, key: str) -> bool:
        store_path = self._get_store_path(key)
        return store_path.exists()

    def query_klines(
        self,
        symbol: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for csv_file in self.store_dir.glob("*.csv"):
            klines = self._read_kline_file(csv_file, period, limit)
            results.extend(klines)

        return results

    def _read_kline_file(
        self,
        file_path: Path,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if period and row.get("period") != period:
                        continue
                    results.append({
                        "name": row.get("name", ""),
                        "symbol": row.get("symbol", ""),
                        "period": row.get("period", ""),
                        "open": float(row.get("open", 0)),
                        "close": float(row.get("close", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "volume": int(row.get("volume", 0)),
                    })
        except Exception:
            return []

        if limit:
            results = results[:limit]
        return results

    def save_kline(
        self,
        name: str,
        symbol: str,
        period: str,
        open_price: float,
        close_price: float,
        high_price: float,
        low_price: float,
        volume: int,
    ) -> None:
        kline_file = self._get_kline_path(symbol)
        file_exists = kline_file.exists()

        row: Dict[str, Any] = {
            "symbol": symbol,
            "name": name,
            "period": period,
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
        }

        csv_file = open(kline_file, "a", encoding="utf-8", newline="")
        try:
            writer = csv.DictWriter(csv_file, fieldnames=KLINE_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        finally:
            csv_file.close()

    def save_klines(self, klines: List[Dict[str, Any]]) -> None:
        if not klines:
            return

        symbol_files: Dict[str, List[Dict[str, Any]]] = {}
        for kline in klines:
            symbol = kline.get("symbol", "")
            if symbol not in symbol_files:
                symbol_files[symbol] = []
            symbol_files[symbol].append(kline)

        for symbol, symbol_klines in symbol_files.items():
            kline_file = self._get_kline_path(symbol)
            file_exists = kline_file.exists()

            with open(kline_file, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=KLINE_COLUMNS)
                if not file_exists:
                    writer.writeheader()
                for kline in symbol_klines:
                    row = {
                        "symbol": kline.get("symbol", ""),
                        "name": kline.get("name", ""),
                        "period": kline.get("period", ""),
                        "open": kline.get("open", 0),
                        "close": kline.get("close", 0),
                        "high": kline.get("high", 0),
                        "low": kline.get("low", 0),
                        "volume": kline.get("volume", 0),
                    }
                    writer.writerow(row)

