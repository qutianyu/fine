import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import KLINE_COLUMNS, STOCK_INFO_COLUMNS, Store


def _get_default_store_dir() -> Path:
    """获取默认缓存目录"""
    try:
        from fine.config import get_config

        return get_config().get_store_dir()
    except Exception:
        import platformdirs

        return Path(platformdirs.user_config_dir("fine")) / ".store"


class CSVStore(Store):
    """CSV file-based store for kline and stock info data

    Usage:
        store = CSVStore()

        # K线数据
        klines = store.load_klines("sh600519", "1d")
        store.save_klines([...])

        # 股票基本信息
        info = store.load_stock_info("sh600519")
        store.save_stock_info({...})
    """

    def __init__(self, store_dir: Optional[str] = None):
        if store_dir:
            self.store_dir = Path(store_dir)
        else:
            self.store_dir = _get_default_store_dir()
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _get_kline_path(self, symbol: str, period: str) -> Path:
        return self.store_dir / f"{symbol}_{period}.csv"

    def load_klines(
        self,
        symbol: str,
        period: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """加载K线数据，支持按日期范围过滤

        Args:
            symbol: 股票代码
            period: 时间周期
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)

        Returns:
            按日期排序的K线数据列表
        """
        kline_file = self._get_kline_path(symbol, period)
        if not kline_file.exists():
            return []

        results = []
        try:
            with open(kline_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row.get("date", "")
                    if start_date and date < start_date:
                        continue
                    if end_date and date > end_date:
                        continue
                    results.append(
                        {
                            "date": date,
                            "name": row.get("name", ""),
                            "symbol": row.get("symbol", ""),
                            "period": row.get("period", ""),
                            "open": float(row.get("open", 0)),
                            "close": float(row.get("close", 0)),
                            "high": float(row.get("high", 0)),
                            "low": float(row.get("low", 0)),
                            "volume": int(row.get("volume", 0)),
                        }
                    )
        except Exception:
            return []

        results.sort(key=lambda x: x.get("date", ""))
        return results

    def save_klines(
        self,
        klines: List[Dict[str, Any]],
        symbol: Optional[str] = None,
        period: Optional[str] = None,
    ) -> None:
        """保存K线数据，按日期排序覆盖写入

        Args:
            klines: K线数据列表
            symbol: 股票代码 (从klines中获取或直接指定)
            period: 时间周期 (从klines中获取或直接指定)
        """
        if not klines:
            return

        if symbol is None:
            symbol = klines[0].get("symbol", "")
        if period is None:
            period = klines[0].get("period", "1d")

        if not symbol or not period:
            return

        kline_file = self._get_kline_path(symbol, period)

        existing = []
        if kline_file.exists():
            existing = self.load_klines(symbol, period)

        existing_map: Dict[str, Dict[str, Any]] = {}
        for item in existing:
            existing_map[item.get("date", "")] = item

        for kline in klines:
            date = kline.get("date", "")
            if date:
                existing_map[date] = kline

        all_klines = list(existing_map.values())
        all_klines.sort(key=lambda x: x.get("date", ""))

        fieldnames = ["date"] + KLINE_COLUMNS

        with open(kline_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for kline in all_klines:
                row = {
                    "date": kline.get("date", ""),
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

    def _get_stock_info_path(self) -> Path:
        return self.store_dir / "stock_info.csv"

    def save_stock_info(self, stock_info: Dict[str, Any]) -> None:
        """保存股票基本面信息

        Args:
            stock_info: 股票基本面数据字典
        """
        if not stock_info:
            return

        symbol = stock_info.get("symbol", "")
        if not symbol:
            return

        info_file = self._get_stock_info_path()
        existing = {}

        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("symbol") == symbol:
                            existing = row
                            break
            except Exception:
                pass

        existing.update(stock_info)

        all_infos = []
        if info_file.exists():
            try:
                with open(info_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("symbol") != symbol:
                            all_infos.append(row)
            except Exception:
                pass

        all_infos.append(existing)

        with open(info_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=STOCK_INFO_COLUMNS)
            writer.writeheader()
            for info in all_infos:
                row = {col: info.get(col, "") for col in STOCK_INFO_COLUMNS}
                writer.writerow(row)

    def load_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """加载股票基本面信息

        Args:
            symbol: 股票代码

        Returns:
            股票基本面数据字典，不存在则返回 None
        """
        info_file = self._get_stock_info_path()
        if not info_file.exists():
            return None

        try:
            with open(info_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("symbol") == symbol:
                        result = {}
                        for col in STOCK_INFO_COLUMNS:
                            val = row.get(col, "")
                            if col not in ("symbol", "name", "source"):
                                try:
                                    result[col] = float(val) if val else 0.0
                                except ValueError:
                                    result[col] = 0.0
                            else:
                                result[col] = val
                        return result
        except Exception:
            pass

        return None

    def get(self, key: str) -> Optional[Any]:
        store_path = self.store_dir / f"{key}.json"
        if not store_path.exists():
            return None
        try:
            import json

            with open(store_path, "r", encoding="utf-8") as f:
                content = f.read()
                return json.loads(content) if content else None
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        import json

        store_path = self.store_dir / f"{key}.json"
        with open(store_path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)

    def delete(self, key: str) -> bool:
        store_path = self.store_dir / f"{key}.json"
        if store_path.exists():
            store_path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        store_path = self.store_dir / f"{key}.json"
        return store_path.exists()

    def query_klines(
        self,
        symbol: Optional[str] = None,
        period: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for csv_file in self.store_dir.glob("*.csv"):
            if csv_file.name == "stock_info.csv":
                continue
            try:
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if symbol and row.get("symbol") != symbol:
                            continue
                        if period and row.get("period") != period:
                            continue
                        results.append(
                            {
                                "date": row.get("date", ""),
                                "name": row.get("name", ""),
                                "symbol": row.get("symbol", ""),
                                "period": row.get("period", ""),
                                "open": float(row.get("open", 0)),
                                "close": float(row.get("close", 0)),
                                "high": float(row.get("high", 0)),
                                "low": float(row.get("low", 0)),
                                "volume": int(row.get("volume", 0)),
                            }
                        )
            except Exception:
                continue

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
        kline_file = self._get_kline_path(symbol, period)
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

        with open(kline_file, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=KLINE_COLUMNS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def clear(self) -> None:
        for file in self.store_dir.iterdir():
            if file.suffix in (".csv", ".json"):
                file.unlink()
