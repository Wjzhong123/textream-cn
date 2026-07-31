"""
One Memory MCP 客户端

通过 MCP 协议与 One Memory 通信
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from .exceptions import OneMemoryError, ConnectionError

logger = logging.getLogger(__name__)


class OneMemoryClient:
    """
    One Memory MCP 客户端（真实实现）

    通过 stdio 与 One Memory MCP 服务器通信，支持连接重用。
    """

    # 连接空闲超时：120秒内无请求则自动关闭（避免频繁创建/销毁子进程）
    KEEPALIVE_TTL = int(os.environ.get("OH_MEMORY_KEEPALIVE_TTL", "120"))
    STARTUP_TIMEOUT = 15.0

    def __init__(self, mcp_url: str = "http://localhost:3000"):
        """
        初始化 MCP 客户端

        Args:
            mcp_url: One Memory MCP 服务地址（仅用于兼容旧接口，实际使用 stdio）
        """
        self.mcp_url = mcp_url
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.Task | None = None
        self._read_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._last_call: float = 0
        self._keepalive_task: asyncio.Task | None = None
        self._request_id: int = 0
        self._pending: dict[int | str, asyncio.Future] = {}
        self._initialized: bool = False
        self._init_event: asyncio.Event | None = None
        self._init_error: Exception | None = None

    async def connect(self):
        """连接到 One Memory MCP 服务"""
        try:
            await self._start()
            logger.info(f"✅ 已连接到 One Memory MCP")
        except Exception as e:
            raise ConnectionError(f"无法连接到 One Memory MCP: {e}")

    async def _start(self):
        """启动 MCP 子进程（支持连接重用）"""
        # 如果进程已存在且运行中，直接返回（重用现有连接）
        if self._process and self._process.returncode is None:
            self._last_call = time.time()
            logger.debug("[OneMemoryClient] 重用现有 MCP 连接 (PID=%d)", self._process.pid)
            return

        # 重置握手状态
        self._init_event = asyncio.Event()
        self._init_error = None

        # 查找 MCP 服务器脚本
        script_path = self._find_mcp_script()
        logger.debug(f"[OneMemoryClient] MCP 脚本路径: {script_path}")

        # 准备环境变量
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # 启动子进程
        is_windows = os.name == "nt"
        ext = script_path.suffix.lower()

        if ext == ".sh":
            executable = "/bin/bash" if not is_windows else "bash"
            args: list[str] = [str(script_path)]
        elif ext == ".bat":
            executable = os.environ.get("COMSPEC", "cmd.exe")
            args = ["/c", str(script_path)]
        elif ext == ".js":
            executable = "node"
            args = [str(script_path)]
        elif ext == ".ts":
            executable = "npx"
            args = ["--yes", "tsx", str(script_path)]
        else:
            # .py 或其他
            executable = sys.executable
            args = [str(script_path)]

        # 传入 codegraph-dir 参数
        codegraph_dir = self._find_codegraph_dir()
        if codegraph_dir:
            args.extend(["--codegraph-dir", str(codegraph_dir)])

        logger.debug(f"[OneMemoryClient] 启动 MCP 进程: {executable} {' '.join(args)}")

        self._process = await asyncio.create_subprocess_exec(
            executable, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        logger.debug(f"[OneMemoryClient] MCP 进程已启动 (PID={self._process.pid})")

        # 启动后台任务
        self._reader = asyncio.create_task(self._read_stdout())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        self._last_call = time.time()
        self._initialized = False

        # 后台执行握手
        # 保存 task 引用防止 GC 回收（Moat firehose 规则）
        self._handshake_task = asyncio.create_task(self._do_handshake())

    def _find_mcp_script(self) -> Path:
        """查找 One Memory MCP 服务器脚本"""
        # 优先从 ONE_ROOT 环境变量定位
        one_root = os.environ.get("ONE_ROOT")
        if one_root:
            root = Path(one_root)
            candidates = [
                # AI-memory standalone repo 结构
                root / "bin" / "one-memory-mcp.sh",
                root / "packages" / "memory-mcp" / "build" / "index.js",
                root / "packages" / "memory-mcp" / "src" / "index.ts",
                # One OS 完整项目结构 (向后兼容)
                root / "packages" / "backend" / "bin" / "mcp" / "one-memory-mcp.sh",
                root / "backend" / "bin" / "mcp" / "one-memory-mcp.sh",
                root / "packages" / "one-memory-mcp" / "build" / "index.js",
                root / "packages" / "one-memory-mcp" / "src" / "index.ts",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate

        # 从当前文件向上查找 One 项目根目录
        current = Path(__file__).resolve().parent
        for _ in range(15):
            # 开发模式：包含 packages/one-memory-mcp
            if (current / "packages" / "one-memory-mcp").exists():
                mcp_sh = current / "packages" / "backend" / "bin" / "mcp" / "one-memory-mcp.sh"
                if mcp_sh.exists():
                    return mcp_sh
                # 直接使用 TypeScript 源码
                mcp_ts = current / "packages" / "one-memory-mcp" / "src" / "index.ts"
                if mcp_ts.exists():
                    return mcp_ts
                mcp_js = current / "packages" / "one-memory-mcp" / "build" / "index.js"
                if mcp_js.exists():
                    return mcp_js

            # Electron 打包模式
            mcp_sh = current / "backend" / "bin" / "mcp" / "one-memory-mcp.sh"
            if mcp_sh.exists():
                return mcp_sh

            parent = current.parent
            if parent == current:
                break
            current = parent

        # 兜底：返回最可能的路径（让错误更清晰）
        raise ConnectionError(
            "找不到 One Memory MCP 服务器脚本。\n"
            "请确保 ONE_ROOT 环境变量已设置，或在 One 项目根目录下运行。"
        )

    def _find_codegraph_dir(self) -> Path | None:
        """查找 codegraph 数据目录"""
        # 1. 环境变量
        if env_dir := os.environ.get("ONE_MEMORY_CODEGRAPH_DIR"):
            return Path(env_dir)

        # 2. ONE_ROOT (AI-memory 或 One OS)
        if one_root := os.environ.get("ONE_ROOT"):
            candidate = Path(one_root) / ".codegraph"
            if candidate.exists():
                return candidate

        # 3. AI-memory repo 默认 codegraph 目录
        ai_memory_codegraph = Path.home() / "Desktop" / "AI-memory" / ".codegraph"
        if ai_memory_codegraph.exists():
            return ai_memory_codegraph

        # 4. 默认位置（macOS - One OS Electron）
        default = Path.home() / "Library" / "Application Support" / "@one" / "electron" / ".codegraph"
        if default.exists():
            return default

        return None

    async def _do_handshake(self):
        """MCP 协议握手"""
        if not self._init_event or not self._process or not self._process.stdin:
            return

        try:
            init_req = {
                "jsonrpc": "2.0",
                "id": "__init__",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "OneMemoryClient", "version": "1.0.0"},
                },
            }
            self._pending["__init__"] = asyncio.get_event_loop().create_future()
            self._process.stdin.write((json.dumps(init_req) + "\n").encode("utf-8"))
            await self._process.stdin.drain()

            init_resp = await asyncio.wait_for(
                self._pending["__init__"], timeout=self.STARTUP_TIMEOUT
            )
            self._pending.pop("__init__", None)

            if "error" not in init_resp:
                # 发送 initialized 通知
                notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                self._process.stdin.write((json.dumps(notif) + "\n").encode("utf-8"))
                await self._process.stdin.drain()
                self._initialized = True
                logger.info("[OneMemoryClient] MCP 握手完成")
                self._init_event.set()
            else:
                err_msg = str(init_resp.get("error"))
                logger.warning(f"[OneMemoryClient] 握手失败: {err_msg}")
                self._init_error = RuntimeError(err_msg)
                self._init_event.set()

        except asyncio.TimeoutError:
            self._pending.pop("__init__", None)
            logger.warning("[OneMemoryClient] 握手超时（降级模式）")
            self._init_error = TimeoutError("MCP 握手超时")
            self._init_event.set()
        except Exception as e:
            self._pending.pop("__init__", None)
            logger.warning(f"[OneMemoryClient] 握手异常: {e}")
            self._init_error = e
            self._init_event.set()

    async def _read_stdout(self):
        """读取 MCP 子进程 stdout"""
        try:
            while self._process and self._process.stdout:
                line = await self._process.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode("utf-8").strip())
                    req_id = msg.get("id")
                    if req_id is not None and req_id in self._pending:
                        future = self._pending.pop(req_id)
                        if not future.done():
                            future.set_result(msg)
                    elif msg.get("type") == "ready":
                        self._read_queue.put_nowait(msg)
                    elif msg.get("type") == "log":
                        logger.debug(f"[OneMemoryClient:child] {msg.get('text', '')}")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.warning(f"[OneMemoryClient] reader error: {e}")

    async def _keepalive_loop(self):
        """监控连接空闲时间，超时则关闭进程"""
        while self._process and self._process.returncode is None:
            await asyncio.sleep(5)
            idle_time = time.time() - self._last_call
            if idle_time > self.KEEPALIVE_TTL:
                logger.info(
                    f"[OneMemoryClient] 连接空闲 {int(idle_time)}s > TTL {self.KEEPALIVE_TTL}s，自动关闭"
                )
                await self.shutdown()
                break

    async def call(self, method: str, params: dict | None = None) -> dict:
        """
        调用 MCP 方法

        Args:
            method: 方法名（如 "tools/call"、"initialize"）
            params: 参数

        Returns:
            响应字典
        """
        await self._start()

        # 等待握手完成
        if self._init_event and not self._init_event.is_set():
            try:
                await asyncio.wait_for(self._init_event.wait(), timeout=self.STARTUP_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning("[OneMemoryClient] 等待握手超时，继续尝试...")

        if self._init_error:
            logger.warning(f"[OneMemoryClient] 握手未成功: {self._init_error}")

        self._request_id += 1
        req = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }
        self._pending[self._request_id] = asyncio.get_event_loop().create_future()

        try:
            if self._process and self._process.stdin:
                self._process.stdin.write((json.dumps(req) + "\n").encode("utf-8"))
                await self._process.stdin.drain()
            self._last_call = time.time()
            return await asyncio.wait_for(self._pending[self._request_id], timeout=30.0)
        except asyncio.TimeoutError:
            self._pending.pop(self._request_id, None)
            return {"error": "timeout"}
        except Exception as e:
            self._pending.pop(self._request_id, None)
            return {"error": str(e)}

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称（如 "memory_write"、"memory_query"）
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._initialized and self._init_error:
            # 如果握手失败，返回错误但不抛出异常（允许降级）
            logger.warning(f"[OneMemoryClient] MCP 未初始化: {self._init_error}")

        result = await self.call("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })

        # 解析工具调用结果
        if "error" in result:
            error_msg = result["error"] if isinstance(result["error"], str) else str(result["error"])
            logger.error(f"[OneMemoryClient] 工具调用失败 {tool_name}: {error_msg}")
            return {"status": "error", "message": error_msg}

        # 提取工具返回的内容
        content = result.get("result", {}).get("content", [])
        if content and len(content) > 0:
            first = content[0]
            if first.get("type") == "text":
                try:
                    # 尝试解析 JSON
                    return json.loads(first["text"])
                except json.JSONDecodeError:
                    # 返回纯文本
                    return {"status": "ok", "text": first["text"]}

        return {"status": "ok", "result": result}

    async def close(self):
        """关闭连接"""
        await self.shutdown()

    async def shutdown(self):
        """完全关闭 MCP 进程和所有后台任务"""
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        if self._reader and not self._reader.done():
            self._reader.cancel()
            try:
                await self._reader
            except asyncio.CancelledError:
                pass
            self._reader = None

        if self._process and self._process.returncode is None:
            try:
                self._process.kill()
                await self._process.wait()
            except ProcessLookupError:
                pass
            self._process = None

        self._initialized = False
        if self._init_event:
            self._init_event.clear()
        logger.info("👋 One Memory MCP 连接已关闭")
