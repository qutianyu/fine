import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class TaskManager:
    """任务管理器

    管理用户的回测任务，包括配置、策略代码、交易记录和执行结果。

    Usage:
        manager = TaskManager(work_dir=".")

        # 创建任务
        task_id = manager.create_task(config={"cash": 1000000, "symbols": ["sh600519"]})

        # 添加交易记录
        manager.add_trade(task_id, {
            "action": "buy",
            "symbol": "sh600519",
            "price": 1800.0,
            "shares": 100,
            "success": True,
        })

        # 设置结果
        manager.set_result(task_id, "# 回测结果\\n\\n最终收益: 10%")

        # 获取任务
        task = manager.get_task(task_id)
    """

    def __init__(self, work_dir: str = "."):
        """初始化任务管理器

        Args:
            work_dir: 工作目录，任务数据将保存在此目录下的 tasks 文件夹中
        """
        self.work_dir = Path(work_dir)
        self.tasks_dir = self.work_dir / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _get_task_dir(self, task_id: str) -> Path:
        """获取任务目录"""
        return self.tasks_dir / task_id

    def _get_config_path(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "config.json"

    def _get_strategy_path(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "strategy.py"

    def _get_trades_path(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "trades.json"

    def _get_result_path(self, task_id: str) -> Path:
        return self._get_task_dir(task_id) / "result.md"

    def create_task(
        self,
        config: dict[str, Any],
        strategy_code: Optional[str] = None,
    ) -> str:
        """创建新任务

        Args:
            config: 任务配置，包含 cash, symbols, fee_rate, date 等
            strategy_code: 策略代码（可选）

        Returns:
            任务ID（时间戳）
        """
        task_id = str(int(datetime.now().timestamp() * 1000))

        task_dir = self._get_task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)

        config["task_id"] = task_id
        config["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self._get_config_path(task_id), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        if strategy_code:
            with open(self._get_strategy_path(task_id), "w", encoding="utf-8") as f:
                f.write(strategy_code)

        with open(self._get_trades_path(task_id), "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

        return task_id

    def get_task(self, task_id: str) -> dict[str, Any]:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典，包含 config, strategy_code, trades, result
        """
        task_dir = self._get_task_dir(task_id)
        if not task_dir.exists():
            raise ValueError(f"Task {task_id} not found")

        result = {"task_id": task_id}

        config_path = self._get_config_path(task_id)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                result["config"] = json.load(f)

        strategy_path = self._get_strategy_path(task_id)
        if strategy_path.exists():
            with open(strategy_path, "r", encoding="utf-8") as f:
                result["strategy_code"] = f.read()

        trades_path = self._get_trades_path(task_id)
        if trades_path.exists():
            with open(trades_path, "r", encoding="utf-8") as f:
                result["trades"] = json.load(f)

        result_path = self._get_result_path(task_id)
        if result_path.exists():
            with open(result_path, "r", encoding="utf-8") as f:
                result["result"] = f.read()

        return result

    def get_config(self, task_id: str) -> dict[str, Any]:
        """获取任务配置

        Args:
            task_id: 任务ID

        Returns:
            任务配置
        """
        config_path = self._get_config_path(task_id)
        if not config_path.exists():
            raise ValueError(f"Task {task_id} not found")

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_config(self, task_id: str, config: dict[str, Any]) -> None:
        """更新任务配置

        Args:
            task_id: 任务ID
            config: 新的配置
        """
        config_path = self._get_config_path(task_id)
        if not config_path.exists():
            raise ValueError(f"Task {task_id} not found")

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def add_trade(self, task_id: str, trade: dict[str, Any]) -> None:
        """添加交易记录

        Args:
            task_id: 任务ID
            trade: 交易记录
        """
        trades_path = self._get_trades_path(task_id)
        if not trades_path.exists():
            with open(trades_path, "w", encoding="utf-8") as f:
                json.dump([], f)

        with open(trades_path, "r", encoding="utf-8") as f:
            trades = json.load(f)

        trade["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trades.append(trade)

        with open(trades_path, "w", encoding="utf-8") as f:
            json.dump(trades, f, ensure_ascii=False, indent=2)

    def get_trades(self, task_id: str) -> list[dict[str, Any]]:
        """获取交易记录

        Args:
            task_id: 任务ID

        Returns:
            交易记录列表
        """
        trades_path = self._get_trades_path(task_id)
        if not trades_path.exists():
            return []

        with open(trades_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def set_result(self, task_id: str, result: str) -> None:
        """设置执行结果

        Args:
            task_id: 任务ID
            result: 执行结果（markdown 格式）
        """
        result_path = self._get_result_path(task_id)
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(result)

    def get_result(self, task_id: str) -> Optional[str]:
        """获取执行结果

        Args:
            task_id: 任务ID

        Returns:
            执行结果（markdown 格式），不存在返回 None
        """
        result_path = self._get_result_path(task_id)
        if not result_path.exists():
            return None

        with open(result_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_tasks(self) -> list[str]:
        """列出所有任务ID

        Returns:
            任务ID列表（按创建时间倒序）
        """
        if not self.tasks_dir.exists():
            return []

        tasks = []
        for task_dir in self.tasks_dir.iterdir():
            if task_dir.is_dir():
                tasks.append(task_dir.name)

        tasks.sort(reverse=True)
        return tasks

    def delete_task(self, task_id: str) -> bool:
        """删除任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功删除
        """
        import shutil

        task_dir = self._get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)
            return True
        return False
