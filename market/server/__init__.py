"""
Fine Server - FastAPI-based service for running backtests

Usage:
    fine start --config server_config.json
"""

import json
import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    type: str
    config: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    result_file: Optional[str] = None


class ServerConfig:
    """Server configuration"""
    
    def __init__(self, config_path: str = "server_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        if Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        return {
            "host": "0.0.0.0",
            "port": 8080,
            "work_dir": "./fine_tasks",
            "lang": "zh",
            "cache": {
                "type": "sqlite",
                "cache_dir": "./fine_cache"
            }
        }
    
    @property
    def host(self) -> str:
        return self.config.get("host", "0.0.0.0")
    
    @property
    def port(self) -> int:
        return self.config.get("port", 8080)
    
    @property
    def work_dir(self) -> str:
        return self.config.get("work_dir", "./fine_tasks")
    
    @property
    def lang(self) -> str:
        return self.config.get("lang", "zh")
    
    @property
    def cache_config(self) -> Dict[str, Any]:
        return self.config.get("cache", {"type": "memory"})


class TaskManager:
    """Manages tasks in memory"""

    def __init__(self, work_dir: str = "./fine_tasks"):
        self.tasks: Dict[str, Task] = {}
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, task_type: str, config: Dict[str, Any]) -> Task:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            id=task_id,
            type=task_type,
            config=config,
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        result_file: Optional[str] = None,
    ) -> None:
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            if status == TaskStatus.RUNNING:
                task.started_at = datetime.now().isoformat()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.completed_at = datetime.now().isoformat()
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if result_file is not None:
                task.result_file = result_file


# Global instances (initialized by start_server)
server_config: Optional[ServerConfig] = None
task_manager: Optional[TaskManager] = None
server_cache = None

# FastAPI app
app = FastAPI(title="Fine Server", version="1.0.0")


def get_server_config() -> ServerConfig:
    global server_config
    if server_config is None:
        server_config = ServerConfig()
    return server_config


def get_task_manager() -> TaskManager:
    global task_manager
    if task_manager is None:
        config = get_server_config()
        task_manager = TaskManager(config.work_dir)
    return task_manager


def get_cache():
    """Get or create cache instance"""
    global server_cache
    if server_cache is None:
        from market.cache import get_cache
        config = get_server_config()
        cache_cfg = config.cache_config
        cache_type = cache_cfg.get("type", "memory")
        server_cache = get_cache(cache_type, **cache_cfg)
    return server_cache


@app.get("/")
def root():
    return {"message": "Fine Server API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/config")
def get_config():
    """Get server configuration (non-sensitive parts)"""
    config = get_server_config()
    return {
        "host": config.host,
        "port": config.port,
        "lang": config.lang,
        "cache_type": config.cache_config.get("type", "memory"),
    }


@app.post("/tasks")
def create_task(request: Dict[str, Any]):
    """Create a new task"""
    task_type = request.get("type", "backtest")
    config = request.get("config", {})

    # Merge with server config
    server_cfg = get_server_config()
    if "lang" not in config:
        config["lang"] = server_cfg.lang
    if "work_dir" not in config:
        config["work_dir"] = server_cfg.work_dir
    if "cache" not in config:
        config["cache"] = server_cfg.cache_config

    manager = get_task_manager()
    task = manager.create_task(task_type, config)

    import threading
    thread = threading.Thread(target=run_task, args=(task.id, task_type, config))
    thread.start()

    return {
        "task_id": task.id,
        "status": task.status,
        "message": f"Task created successfully",
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get task status and result"""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    response = {
        "id": task.id,
        "type": task.type,
        "status": task.status,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
    }

    if task.error:
        response["error"] = task.error

    if task.status == TaskStatus.COMPLETED:
        if task.result_file:
            response["result_file"] = task.result_file
        if task.result:
            response["result"] = task.result

    return response


@app.get("/tasks/{task_id}/result")
def get_task_result(task_id: str):
    """Get task result as markdown file"""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.COMPLETED:
        return {"status": task.status, "message": "Task not completed yet"}

    if not task.result_file:
        return {"message": "No result file available"}

    if not Path(task.result_file).exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(task.result_file, media_type="text/markdown")


@app.get("/tasks")
def list_tasks():
    """List all tasks"""
    manager = get_task_manager()
    tasks = []
    for task in manager.tasks.values():
        tasks.append({
            "id": task.id,
            "type": task.type,
            "status": task.status,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        })
    return {"tasks": tasks}


def run_task(task_id: str, task_type: str, config: Dict[str, Any]) -> None:
    """Run the task in background"""
    manager = get_task_manager()
    manager.update_task(task_id, TaskStatus.RUNNING)

    try:
        if task_type == "backtest":
            result = run_backtest_task(config)
            manager.update_task(
                task_id,
                TaskStatus.COMPLETED,
                result=result,
                result_file=result.get("result_file"),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    except Exception as e:
        manager.update_task(
            task_id, TaskStatus.FAILED, error=str(e)
        )


def run_backtest_task(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run backtest task with cache"""
    from market.cli.commands import (
        run_backtest,
        ensure_timestamp,
        get_work_dir,
    )

    # Get cache
    cache = get_cache()
    provider_name = config.get("provider", "akshare")

    # Ensure timestamp for result files
    ensure_timestamp(config)

    # Get work directory
    work_dir = get_work_dir(config)

    # Generate result file path
    ts = config.get("_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
    result_file = os.path.join(work_dir, f"result_{ts}.md")

    # Fetch data with cache
    symbols = config.get("symbols", [])
    start_date = config.get("date", {}).get("start", config.get("start_date"))
    end_date = config.get("date", {}).get("end", config.get("end_date"))
    period = config.get("period", "daily")

    # Pre-fetch and cache data for all symbols
    from market.providers import create_provider
    provider = create_provider(provider_name)

    for symbol in symbols:
        cache_key = f"kline:{symbol}:{period}:{start_date}:{end_date}"
        
        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            print(f"Cache hit for {symbol}")
            continue
        
        # Cache miss - fetch from API
        print(f"Cache miss for {symbol}, fetching...")
        klines = provider.get_kline(
            symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Update cache
        if klines:
            # Convert to dict for caching
            cache_data = [
                {
                    "date": kl.date,
                    "open": kl.open,
                    "high": kl.high,
                    "low": kl.low,
                    "close": kl.close,
                    "volume": kl.volume,
                }
                for kl in klines
            ]
            cache.set(cache_key, cache_data, ttl=86400)  # 24 hours

    # Run backtest
    result = run_backtest(config)

    # Return result summary
    return {
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "result_file": result_file,
        "metrics": {
            "total_return": getattr(result.metrics, "total_return", 0),
            "annualized_return": getattr(result.metrics, "annualized_return", 0),
            "sharpe_ratio": getattr(result.metrics, "sharpe_ratio", 0),
            "max_drawdown": getattr(result.metrics, "max_drawdown", 0),
            "win_rate": getattr(result.metrics, "win_rate", 0),
            "total_trades": getattr(result.metrics, "total_trades", 0),
        },
    }


def start_server(
    config_path: str = "server_config.json",
    port: Optional[int] = None,
    host: Optional[str] = None,
    work_dir: Optional[str] = None,
):
    """Start the Fine server"""
    global server_config, task_manager, server_cache

    # Load config
    server_config = ServerConfig(config_path)
    
    # Override with CLI args if provided
    if port is not None:
        server_config.config["port"] = port
    if host is not None:
        server_config.config["host"] = host
    if work_dir is not None:
        server_config.config["work_dir"] = work_dir

    # Initialize task manager
    task_manager = TaskManager(server_config.work_dir)

    # Initialize cache
    cache_cfg = server_config.cache_config
    cache_type = cache_cfg.get("type", "memory")
    # Extract only valid kwargs (exclude 'type'), use work_dir as default cache_dir
    cache_kwargs = {k: v for k, v in cache_cfg.items() if k != "type"}
    if "cache_dir" not in cache_kwargs:
        cache_kwargs["cache_dir"] = os.path.join(server_config.work_dir, "cache")
    from market.cache import get_cache
    server_cache = get_cache(cache_type, **cache_kwargs)

    print(f"Starting Fine server on {server_config.host}:{server_config.port}")
    print(f"Work directory: {server_config.work_dir}")
    print(f"Language: {server_config.lang}")
    print(f"Cache: {cache_type}")
    print(f"API documentation: http://localhost:{server_config.port}/docs")

    uvicorn.run(app, host=server_config.host, port=server_config.port, log_level="info")


if __name__ == "__main__":
    start_server()
