"""
Fine 配置管理

配置文件位置:
- macOS: ~/.config/fine/fine.json
- Linux/Windows: 使用 platformdirs 标准路径
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _get_config_dir() -> Path:
    """获取配置目录路径"""
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~/.config/fine"))
    else:
        import platformdirs

        return Path(platformdirs.user_config_dir("fine"))


DEFAULT_CONFIG = {
    "provider": "akshare",
    "period": "1d",
    "lang": "zh",
}


class Config:
    """Fine 配置类"""

    def __init__(self):
        self.config_dir = _get_config_dir()
        self.config_file = self.config_dir / "fine.json"
        self.store_dir = self.config_dir / "store"
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载配置文件"""
        self._ensure_dir()
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = DEFAULT_CONFIG.copy()
                self._save()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self._save()

    def _ensure_dir(self) -> None:
        """确保目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        """保存配置文件"""
        self._ensure_dir()
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value
        self._save()

    @property
    def provider(self) -> str:
        """默认数据提供商"""
        return self._config.get("provider", "akshare")

    @property
    def period(self) -> str:
        """默认周期"""
        return self._config.get("period", "1d")

    @property
    def lang(self) -> str:
        """语言设置 (zh/en)"""
        return self._config.get("lang", "zh")

    def get_store_dir(self) -> Path:
        """获取缓存目录"""
        self._ensure_dir()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        return self.store_dir


_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


__all__ = ["Config", "get_config"]
